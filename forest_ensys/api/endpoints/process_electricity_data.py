# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from forest_ensys import crud, schemas
from forest_ensys.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.ProcessElectricity])
def get_all_process_electricity_data(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> List[schemas.ProcessElectricity]:
    """
    Retrieve all electricity data
    """
    process_electricity_data = crud.process_electricity.get_multi(
        db=db, skip=skip, limit=limit
    )
    return process_electricity_data


@router.post("/", response_model=schemas.ProcessElectricity)
def add_process_electricity_data(
    request: schemas.ProcessElectricityCreate,
    db: Session = Depends(deps.get_db),
):
    """
    Create a new process_electricity
    """
    return crud.process_electricity.create(db=db, obj_in=request)
