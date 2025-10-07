# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from forest_ensys.crud.base import CRUDBase
from forest_ensys.model import Model
from forest_ensys.schemas import ModelCreate, ModelUpdate


class CRUDModel(CRUDBase[Model, ModelCreate, ModelUpdate]):
    def create(self, db: Session, *, obj_in: ModelCreate) -> Model:
        """
        Creates a new Model object.
        """
        obj_in_dict = obj_in.dict()
        obj_in_dict["model"] = obj_in_dict["model"]
        db_obj = super().create(db, obj_in=obj_in_dict)
        return db_obj

    def get_by_name(self, db: Session, *, name: str) -> Optional[Model]:
        db_obj = (
            db.query(Model)
            .filter(func.json_extract(Model.model, "$.model.name") == name)
            .first()
        )
        return db_obj


model = CRUDModel(Model)
