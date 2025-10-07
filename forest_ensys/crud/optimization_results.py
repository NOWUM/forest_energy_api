# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional, Any
from sqlalchemy.orm import Session
from forest_ensys.crud.base import CRUDBase
from forest_ensys.model import OptimizationResult


class CRUDOptimizationResults(CRUDBase[OptimizationResult, Any, Any]):
    def create(self, db: Session, *, obj_in: OptimizationResult) -> OptimizationResult:
        db_obj = super().create(db, obj_in=obj_in)
        return db_obj

    def get(
        self, db: Session, *, optimization_case_name: str
    ) -> Optional[OptimizationResult]:
        return (
            db.query(self.model)
            .filter(
                self.model.name == optimization_case_name,
            )
            .first()
        )

    def delete(self, db: Session) -> None:
        db.query(self.model).delete()
        db.commit()

    def delete_by_optimization_case_name(
        self, db: Session, *, optimization_case_name: str
    ) -> None:
        db.query(self.model).filter(
            self.model.name == optimization_case_name,
        ).delete()
        db.commit()


optimization_results = CRUDOptimizationResults(OptimizationResult)
