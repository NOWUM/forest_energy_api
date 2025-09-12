# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from forest_ensys import crud, model, schemas
from forest_ensys.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.ProcessHeat])
def get_all_process_heat_data(
    db: Session = Depends(deps.get_db),
    current: model.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> List[model.ProcessHeat]:
    """
    Retrieve all heat data
    """
    process_heat_data = crud.process_heat.get_multi(
        db=db, user_id=current.id, skip=skip, limit=limit
    )
    return process_heat_data


@router.post("/", response_model=schemas.ProcessHeat)
def add_process_heat_data(
    request: schemas.ProcessHeatCreate,
    db: Session = Depends(deps.get_db),
    current: model.User = Depends(deps.get_current_user),
) -> model.ProcessHeat:
    """
    Create a new process heat data
    """
    return crud.process_heat.create(db=db, obj_in=request, user_id=current.id)
