# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List

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
from sqlalchemy.orm import Session
from forest_ensys import crud, schemas
from forest_ensys.api import deps
from forest_ensys.core.timeseries_helpers import ensure_consistent_granularity
import pandas as pd
from datetime import datetime
from io import StringIO

router = APIRouter()


@router.get("/", response_model=List[schemas.Prices])
def get_all_price_data(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> List[schemas.Prices]:
    """
    Retrieve all price data
    """
    price_data = crud.prices.get_multi(db=db, skip=skip, limit=limit)
    return price_data


@router.get(
    "/names",
    response_model=List[str],
    responses={
        200: {"content": {"application/json": {"example": ["smard", "greenPFC"]}}},
        500: {"description": "Internal server error"},
    },
)
def price_sources(
    db: Session = Depends(deps.get_db),
):
    """
    Return distinct dataset names present in the table.
    """
    try:
        names = crud.prices.get_distinct_names(db)
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
def download_price_csv(
    start_date: datetime = Query(
        "2024-01-01", description="Start date for the optimization period."
    ),
    end_date: datetime = Query(
        "2024-12-31", description="End date for the optimization period."
    ),
    source: str = Query("smard", description="Source of the dataset to download."),
    db: Session = Depends(deps.get_db),
):
    try:
        data_df = crud.prices.get_multi_by_date_range_and_source(
            db=db, start_date=start_date, end_date=end_date, source=source
        )
        if data_df is None:
            raise HTTPException(
                status_code=404, detail=f"No dataset found for source='{source}'"
            )
        buf = StringIO()
        data_df.to_csv(buf, index=False)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={source}.csv",
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
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def upload_price_data(
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    delimiter: str = Form(";", description="The delimiter used in the CSV file"),
    skiprows: int = Form(
        3, description="The number of rows to skip until the actual data begins."
    ),
    DateTimeColumn: str = Form(
        "timestamp", description="The name of the column containing the date and time."
    ),
    ValueColumn: str = Form(
        "price", description="The name of the column containing the price."
    ),
    source: str = Form(
        "greenPFC", description="Name describing the source of the price data."
    ),
):
    if (
        not file
        or not delimiter
        or skiprows is None
        or not DateTimeColumn
        or not ValueColumn
        or not source
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required parameters",
        )
    # check if file is excel or csv
    if not file.filename.endswith((".csv", ".xls", ".xlsx")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only CSV and Excel files are allowed.",
        )
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(
                file.file,
                skiprows=skiprows,
                delimiter=delimiter,
                usecols=[DateTimeColumn, ValueColumn],
            )
        else:
            df = pd.read_excel(
                file.file, skiprows=skiprows, usecols=[DateTimeColumn, ValueColumn]
            )
    except pd.errors.EmptyDataError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty/invalid CSV file")
    except Exception as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, f"Error reading CSV file: {str(e)}"
        )
    df.rename(columns={DateTimeColumn: "timestamp", ValueColumn: "price"}, inplace=True)
    df, granularity = ensure_consistent_granularity(df, ignore_timezone=True)  # TODO
    df["source"] = source
    crud.prices.create_multi(db, obj_in=df.to_dict(orient="records"))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "success", "message": "Data uploaded successfully"},
    )


@router.delete(
    "/",
    responses={
        200: {"description": "Data deleted successfully"},
        404: {"description": "Error deleting prices"},
    },
)
def delete_prices(
    db: Session = Depends(deps.get_db),
    source: str = Query(..., description="Source of the prices to delete"),
):
    try:
        crud.prices.delete(db, source=source)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "success", "message": "Data deleted successfully"},
        )
    except Exception as e:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Error deleting prices: {str(e)}"
        )
