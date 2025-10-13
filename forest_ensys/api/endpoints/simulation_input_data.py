# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later


from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status, Query
from fastapi.responses import JSONResponse
import pandas as pd
from sqlalchemy.orm import Session

from forest_ensys import crud
from forest_ensys.api import deps
from forest_ensys.core.timeseries_helpers import ensure_consistent_granularity

router = APIRouter()


# we want a method that receives a excel file and uploads it to the database
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
    name: str = Query(
        "flexibility_timeseries",
        enum=["flexible_device_demand", "total_electricity_demand"],
        description="The name of the simulation input data. 'flexible_device_demand' is the energy demand of the flexible device. 'total_electricity_demand' is the total electricity demand of the building.",
    ),
    delimiter: str = ";",
    skiprows: int = 3,
    DateTimeColumn: str = "DateTime",
    ValueColumn: str = "Value",
    unit: str = Query(
        "m³/h",
        enum=["m³/h", "kWh", "kW"],
        description="The unit of the heat demand. Can be 'm³/h', 'kWh' or 'kW'",
    ),
    heating_value: float = 10.0,
    conversion_factor: float = 0.8,
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
