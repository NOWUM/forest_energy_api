# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from forest_ensys import crud, schemas
from forest_ensys.api import deps
from forest_ensys.core.calliope_model import generate_calliope_model
import pandas as pd
import json

router = APIRouter()


@router.get("/", response_model=List[schemas.Model])
def get_all_model_data(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> List[schemas.Model]:
    """
    Retrieve all contraints data
    """
    model_data = crud.model.get_multi(db=db, skip=skip, limit=limit)
    return model_data


@router.post("/", response_model=schemas.Model)
def add_model_data(
    request: schemas.ModelCreate,
    db: Session = Depends(deps.get_db),
):
    """
    Create a new model
    """
    return crud.model.create(db=db, obj_in=request)


@router.get("/{model_id}/optimize")
def optimize_model_by_id(
    model_id: int,
    start_date: datetime = None,
    end_date: datetime = None,
    db: Session = Depends(deps.get_db),
) -> str:
    """
    Optimize the model by id
    """
    model = crud.model.get(db=db, id=model_id)
    electricity_data = crud.process_electricity.get_multi_by_date_range(
        db=db, start_date=start_date, end_date=end_date
    )
    heat_data = crud.process_heat.get_multi_by_date_range(
        db=db, start_date=start_date, end_date=end_date
    )
    if electricity_data is None or heat_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Electricity data or heat data not found for model {model_id}!",
        )
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Model {model_id} not found!"
        )
    calliope_model = generate_calliope_model(model.model, electricity_data, heat_data)
    calliope_model.build()
    calliope_model.solve()
    # results to html
    calliope_model.to_csv("results.csv")
    return json.dumps(calliope_model.results["cost"][0].to_dict())


@router.get("/{model_name}/optimize_by_name")
def optimize_model_by_name(
    model_name: str,
    start_date: str,
    db: Session = Depends(deps.get_db),
) -> str:
    """
    Optimize the model by name
    """
    model = crud.model.get_by_name(db=db, name=model_name)
    electricity_data = crud.process_electricity.get_from_start_date(
        db=db, start_date=start_date
    )
    electricity_data_df = pd.read_sql(
        electricity_data.statement, electricity_data.session.connection()
    )
    heat_data = crud.process_heat.get_from_start_date(db=db, start_date=start_date)
    heat_data_df = pd.read_sql(heat_data.statement, heat_data.session.connection())
    if electricity_data_df.empty or heat_data_df.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Electricity data or heat data not found for model {model_name}!",
        )
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_name} not found!",
        )
    calliope_model = generate_calliope_model(
        model.model, electricity_data_df, heat_data_df
    )
    calliope_model.run()
    return json.dumps(calliope_model.results["cost"][0].to_dict(), default=str)


@router.delete("/{model_name}", response_model=schemas.Model)
def delete_model_by_name(
    model_name: str,
    db: Session = Depends(deps.get_db),
):
    """
    Delete a model by name
    """
    model = crud.model.get_by_name(db=db, name=model_name)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_name} not found!",
        )
    return crud.model.remove(db=db, id=model.id)
