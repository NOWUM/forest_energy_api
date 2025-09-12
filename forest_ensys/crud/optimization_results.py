# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from forest_ensys.crud.base import CRUDBase
from forest_ensys.model import OptimizationResult


class CRUDOptimizationResults(CRUDBase[OptimizationResult, Any, Any]):
    def create(
        self, db: Session, *, obj_in: OptimizationResult, user_id: int = None
    ) -> OptimizationResult:
        if user_id is not None:
            obj_in["ref_created_by"] = user_id
        db_obj = super().create(db, obj_in=obj_in)
        return db_obj
    
    def get(self, db: Session, *, user_id: int, optimization_case_name: str) -> Optional[OptimizationResult]:
        return db.query(self.model).filter(
            self.model.ref_created_by == user_id,
            self.model.name == optimization_case_name,
        ).first()
    
    def delete(self, db: Session, *, user_id: int) -> None:
        db.query(self.model).filter(self.model.ref_created_by == user_id).delete()
        db.commit()
        
    def delete_by_user_id_and_optimization_case_name(
        self, db: Session, *, user_id: int, optimization_case_name: str
    ) -> None:
        db.query(self.model).filter(
            self.model.ref_created_by == user_id,
            self.model.name == optimization_case_name,
        ).delete()
        db.commit()

optimization_results = CRUDOptimizationResults(OptimizationResult)