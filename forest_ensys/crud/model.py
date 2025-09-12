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
    def create(self, db: Session, *, obj_in: ModelCreate, user_id: int) -> Model:
        """
        Creates a new Model object.
        """
        obj_in_dict = obj_in.dict()
        obj_in_dict["ref_created_by"] = user_id
        obj_in_dict["model"] = obj_in_dict["model"]
        db_obj = super().create(db, obj_in=obj_in_dict)
        # db_obj.model = json.loads(db_obj.model)
        return db_obj

    def get_by_name(self, db: Session, *, name: str) -> Optional[Model]:
        # db_obj = db.query(Model).filter(Model.model["model"]["name"] == name).first()
        db_obj = (
            db.query(Model)
            .filter(func.json_extract(Model.model, "$.model.name") == name)
            .first()
        )
        return db_obj
        # if db_obj is not None:
        #     obj_out_dict = db_obj.model
        # else:
        #     obj_out_dict = None
        # return obj_out_dict


model = CRUDModel(Model)
