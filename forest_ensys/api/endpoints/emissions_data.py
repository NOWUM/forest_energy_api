# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Text, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from forest_ensys import crud, model, schemas
from forest_ensys.api import deps
from forest_ensys.core import crawlers

router = APIRouter()


@router.get("/", response_model=List[schemas.Emissions])
def get_all_emissions_data(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> List[schemas.Emissions]:
    """
    Retrieve all emissions data
    """
    emissions_data = crud.emissions.get_multi(db=db, skip=skip, limit=limit)
    return emissions_data


@router.get(
    "/get-specific-emissions-factor", response_model=Optional[schemas.Emissions]
)
def get_emissions_data(
    db: Session = Depends(deps.get_db),
    zone_key: str = "DE",
    emission_type: str = "direct",
    production_mode: str = "gas",
) -> schemas.Emissions:
    """
    Retrieve emissions data for a specific zone and emission type and production mode
    """
    emissions_data = crud.emissions.get_specific_emissions(
        db=db,
        zone_key=zone_key,
        emission_type=emission_type,
        production_mode=production_mode,
    )
    return emissions_data


@router.post(
    "/",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {"message": "Emissions data updated successfully"}
                }
            },
        },
        502: {
            "description": "Server Error",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Could not retrieve emissions data. Server probably offline"
                    }
                }
            },
        },
        409: {
            "description": "Conflict Error",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Emissions data already exists. Please delete first if you want to update."
                    }
                }
            },
        },
    },
)
def update_emissions_data(db: Session = Depends(deps.get_db)) -> Text:
    """
    Retrieve the most recent emissions data
    """
    try:
        timeseries_data = crawlers.crawl_emissions_data()
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve emissions data. Server probably offline",
        )
    timeseries_data.rename(columns={"datetime": "timestamp"}, inplace=True)
    try:
        crud.emissions.create_multi(
            db, obj_in=timeseries_data.to_dict(orient="records")
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "Successful Response",
                "message": "Emissions data updated successfully",
            },
        )
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "status": "Successful Response",
                "message": "Emissions data already exists. Please delete first if you want to update.",
            },
        )


@router.delete(
    "/",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {"message": "Emissions data table deleted successfully"}
                }
            },
        }
    },
)
def delete_emissions_data(db: Session = Depends(deps.get_db)) -> Text:
    """
    Delete all emissions data
    """
    crud.emissions.delete(db=db)
    raise HTTPException(
        status_code=200, detail="Emissions data table deleted successfully"
    )


@router.post(
    "/get_specific_emissions_factor", response_model=Optional[schemas.Emissions]
)
def get_specific_emissions_factor(
    db: Session = Depends(deps.get_db),
    zone_key: str = "DE",
    emission_type: str = "direct",
    production_mode: str = "gas",
) -> schemas.Emissions:
    """
    Retrieve emissions data for a specific zone and emission type and production mode
    """
    return crud.emissions.get_specific_emissions(
        db=db,
        zone_key=zone_key,
        emission_type=emission_type,
        production_mode=production_mode,
    )
