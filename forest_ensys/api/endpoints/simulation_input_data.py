# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later


from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    HTTPException,
    status,
    Query,
    Form,
)
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List
import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
from forest_ensys import crud
from forest_ensys.api import deps
from forest_ensys.core.timeseries_helpers import ensure_consistent_granularity
from io import StringIO

router = APIRouter()


@router.get(
    "/names",
    response_model=List[str],
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": ["flexible_device_demand", "total_electricity_demand"]
                }
            }
        },
        500: {"description": "Internal server error"},
    },
)
def list_simulation_input_names(
    db: Session = Depends(deps.get_db),
):
    """
    Return distinct dataset names present in the table.
    """
    try:
        names = crud.simulation_input_data.get_distinct_names(db)
        return names
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch names: {str(e)}",
        )


@router.get(
    "/dataset",
    responses={200: {"description": "CSV download"}, 404: {"description": "Not found"}},
)
def download_simulation_input_csv(
    start_date: datetime = Query(
        "2024-01-01", description="Start date for the optimization period."
    ),
    end_date: datetime = Query(
        "2024-12-31", description="End date for the optimization period."
    ),
    name: str = Query(..., enum=["flexible_device_demand", "total_electricity_demand"]),
    db: Session = Depends(deps.get_db),
):
    try:
        data_df = crud.simulation_input_data.get_multi_by_date_range_and_name(
            db=db, start_date=start_date, end_date=end_date, name=name
        )
        if data_df is None:
            raise HTTPException(
                status_code=404, detail=f"No dataset found for name='{name}'"
            )
        buf = StringIO()
        data_df.to_csv(buf, index=False)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={name}.csv",
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Data uploaded successfully",
                    }
                }
            }
        },
        400: {"description": "Invalid file format"},
        409: {"description": "Data already exists"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def upload_simulation_input_data(
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    name: str = Form(
        "flexibility_timeseries",
        enum=["flexible_device_demand", "total_electricity_demand"],
        description="The name of the simulation input data. 'flexible_device_demand' is the energy demand of the flexible device. 'total_electricity_demand' is the total electricity demand of the building.",
    ),
    delimiter: str = Form(";", description="The delimiter used in the CSV file"),
    skiprows: int = Form(
        3, description="The number of rows to skip until the actual data begins."
    ),
    DateTimeColumn: str = Form(
        "DateTime", description="The name of the column containing the date and time."
    ),
    ValueColumn: str = Form(
        "Value", description="The name of the column containing the value."
    ),
    unit: str = Form(
        "m³/h",
        enum=["m³/h", "kWh", "kW"],
        description="The unit of the heat demand. Can be 'm³/h', 'kWh' or 'kW'",
    ),
    heating_value: float = Form(
        10.0, description="The heating value of the gas in kWh/m³"
    ),
    conversion_factor: float = Form(
        0.8,
        description="Corrects from operating to standard conditions; shown on your bill or from the network operator.",
    ),
):
    if unit.lower() not in ["m³/h", "kw", "kwh", "m3/h"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid unit. Use 'm³/h', 'kWh' or 'kW'",
        )
    if (
        not file
        or not delimiter
        or skiprows is None
        or not DateTimeColumn
        or not ValueColumn
        or not unit
        or not heating_value
        or not conversion_factor
        or not name
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required parameters",
        )

    try:
        df = pd.read_csv(
            file.file,
            skiprows=skiprows,
            delimiter=delimiter,
            usecols=[DateTimeColumn, ValueColumn],
        )
    except pd.errors.EmptyDataError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty/invalid CSV file")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}",
        )

    # crud.simulation_input_data.delete(db)

    df.rename(columns={DateTimeColumn: "timestamp", ValueColumn: "value"}, inplace=True)
    df, granularity = ensure_consistent_granularity(df)
    df["name"] = name
    if unit.lower() == "m³/h" or unit.lower() == "m3/h":
        df["value"] = df["value"] * heating_value * conversion_factor
    elif unit.lower() == "kw":
        df["value"] = df["value"] * granularity
    crud.simulation_input_data.create_multi(db, obj_in=df.to_dict(orient="records"))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "success", "message": "Data uploaded successfully"},
    )


@router.delete(
    "/",
    responses={
        200: {"description": "Data deleted successfully"},
        400: {"description": "Bad request"},
    },
)
def delete_simulation_input_data(
    db: Session = Depends(deps.get_db),
    name: str = Query(
        "flexibility_timeseries",
        enum=["flexible_device_demand", "total_electricity_demand"],
        description="The name of the simulation input data. 'flexible_device_demand' is the energy demand of the flexible device. 'total_electricity_demand' is the total electricity demand of the building.",
    ),
):
    """
    Delete all simulation input data.
    """
    crud.simulation_input_data.delete_by_name(db, name=name)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "success", "message": "Data deleted successfully"},
    )
