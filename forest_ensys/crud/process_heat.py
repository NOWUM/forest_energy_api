# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

from sqlalchemy.orm import Session

from forest_ensys.crud.base import CRUDBase
from forest_ensys.model import ProcessHeat
from forest_ensys.schemas import ProcessHeatCreate, ProcessHeatUpdate
from datetime import datetime


class CRUDProcessHeat(CRUDBase[ProcessHeat, ProcessHeatCreate, ProcessHeatUpdate]):
    def get_from_start_date(
        self, db: Session, user_id: int, start_date: str
    ) -> Optional[ProcessHeat]:
        return db.query(ProcessHeat).filter(
            ProcessHeat.ref_created_by == user_id, ProcessHeat.timestamp >= start_date
        )

    def create(
        self, db: Session, *, obj_in: ProcessHeatCreate, user_id: int
    ) -> ProcessHeat:
        obj_in_dict = obj_in.dict()
        obj_in_dict["ref_created_by"] = user_id
        db_obj = super().create(db, obj_in=obj_in_dict)
        return db_obj
    


process_heat = CRUDProcessHeat(ProcessHeat)
