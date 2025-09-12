# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List
from sqlalchemy.orm import Session
from forest_ensys.model import FlexiblePower
from forest_ensys.schemas import FlexiblePowerCreate, FlexiblePowerUpdate
from forest_ensys.crud.base import CRUDBase


class CRUDFlexiblePower(
    CRUDBase[FlexiblePower, FlexiblePowerCreate, FlexiblePowerUpdate]
):
    def create(self, db: Session, obj_in: FlexiblePower | FlexiblePowerCreate):
        db_obj = FlexiblePower(**obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # def create_multi(
    #     self, db: Session, *, obj_in: List[FlexiblePowerCreate]
    # ) -> List[FlexiblePower]:
    #     """
    #     Create multiple flexible power objects.
    #     """
    #     db_objs = [FlexiblePower(**obj.dict()) for obj in obj_in]
    #     db.add_all(db_objs)
    #     db.commit()
    #     return db_objs

    def get_multi_flexible_power(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(FlexiblePower).offset(skip).limit(limit).all()
    
    def delete(self, db: Session, user_id: int):
        return db.query(FlexiblePower).filter(FlexiblePower.ref_created_by == user_id).delete()
    
    def delete_by_user_id_and_optimization_case_name(self, db: Session, user_id, optimization_case_name: str):
        return db.query(FlexiblePower).filter(FlexiblePower.ref_created_by == user_id, FlexiblePower.optimization_case_name == optimization_case_name).delete()


flexible_power = CRUDFlexiblePower(FlexiblePower)
