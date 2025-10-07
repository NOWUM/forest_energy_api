# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from forest_ensys import crud, schemas
from forest_ensys.api import deps
from forest_ensys.core.timeseries_helpers import ensure_consistent_granularity
import pandas as pd

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


@router.get("/{source}", response_model=List[schemas.Prices])
def get_price_data_by_source(
    source: str,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> List[schemas.Prices]:
    """
    Retrieve price data by source
    """
    try:
        price_data = crud.prices.get_by_source(
            db=db, source=source, skip=skip, limit=limit
        )
        return price_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/upload-price-data",
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
    delimiter: str = ";",
    skiprows: int = 3,
    DateTimeColumn: str = "timestamp",
    ValueColumn: str = "price",
    source: str = "greenPFC",
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
    "/prices",
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
