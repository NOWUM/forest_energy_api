# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from forest_ensys import crud, model, schemas
from forest_ensys.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.User])
def get_all_users(
    db: Session = Depends(deps.get_db),
    current: model.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> List[schemas.User]:
    """
    Retrieve all users.
    """
    users = crud.user.get_multi(db=db, skip=skip, limit=limit)
    return users
