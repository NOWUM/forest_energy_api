# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Text

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from forest_ensys import crud, model, schemas
from forest_ensys.api import deps

router = APIRouter()

@router.post("/", response_model=schemas.DataParc)
def add_process_data(
    request: schemas.DataParcCreate,
    db: Session = Depends(deps.get_db),
):
    """
    Create a new process data
    """
    return crud.data_parc.create(db=db, obj_in=request)

@router.delete(
    "/",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {"message": "Process data table deleted successfully"}
                }
            }
        },
        502: {
            "description": "Server Error",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Could not retrieve emissions data. Server probably offline"
                    }
                }
            }
        }
    },
)
def delete_process_data(db: Session = Depends(deps.get_db)) -> Text:
    """
    Delete all process data
    """
    crud.data_parc.delete(db=db)
    raise HTTPException(
        status_code=200, detail="Process data table deleted successfully"
    )
