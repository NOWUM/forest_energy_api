# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Text
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from forest_ensys import crud, model, schemas
from forest_ensys.api import deps
from datetime import datetime
from pyomo.environ import ConcreteModel, Var, Objective, SolverFactory, NonNegativeReals, minimize, Constraint

router = APIRouter()

grid_to_factors = {
    "Biomasse": "biomass",
    "Wasserkraft": "hydro",
    "Wind Offshore": "wind",
    "Wind Onshore": "wind",
    "Photovoltaik": "solar",
    "Braunkohle": "coal",
    "Steinkohle": "coal",
    "Erdgas": "gas",
    "Sonstige Konventionelle": "gas",
    "Sonstige Erneuerbare": "solar",
    "Pumpspeicher": "hydro",
}
@router.delete(
    "/",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Footprint data table deleted successfully"
                    }
                }
            },
        }
    },
)
def delete_footprint_data(db: Session = Depends(deps.get_db)) -> Text:
    """
    Delete all footprint data
    """
    crud.footprint.delete(db=db)
    raise HTTPException(
        status_code=200, detail="Footprint data table deleted successfully"
    )

def update_footprint_data(db: Session = Depends(deps.get_db)):
    grid = crud.grid.get_average_co2_by_commodity(db=db)
    footprint_data = []
    for row in grid:
        # this means we have missing data for this 15 mins and the co2 is zero
        if row[1] == 0:
            continue
        footprint_data.append(
            model.Footprint(
                timestamp=row[0],
                co2=row[1] / (row[2] * 1000),
            )
        )
    crud.footprint.create_multi(db=db, obj_in=footprint_data)

@router.get("/", response_model=List[schemas.Footprint])
def get_all_footprint_data(
    db: Session = Depends(deps.get_db),
    current: model.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> List[schemas.Footprint]:
    """
    Retrieve all footprint data
    """
    return crud.footprint.get_multi(db=db, skip=skip, limit=limit)

@router.get("/latest", response_model=schemas.Footprint)
def get_latest_footprint_data(db: Session = Depends(deps.get_db)) -> schemas.Footprint:
    """
    Retrieve the latest footprint data
    """
    return crud.footprint.get_latest(db=db)
