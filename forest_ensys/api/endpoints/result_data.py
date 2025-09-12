# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later


from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from forest_ensys import crud, model
from forest_ensys.api import deps

router = APIRouter()


@router.delete(
    "/",
    responses={
        200: {"description": "Data deleted successfully"},
        400: {"description": "Bad request"},
    },
)
def delete_result_data(
    db: Session = Depends(deps.get_db),
    current: model.User = Depends(deps.get_current_user),
    optimization_case_name: str = Query(
        ..., description="The name of the optimization case."
    ),
):
    try:
        crud.optimization_results.delete_by_user_id_and_optimization_case_name(
            db, user_id=current.id, optimization_case_name=optimization_case_name
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "success", "message": "Data deleted successfully"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An error occurred: {str(e)}",
        )
