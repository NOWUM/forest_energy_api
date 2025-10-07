# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

from sqlalchemy.orm import Session

from forest_ensys.crud.base import CRUDBase
from forest_ensys.model import ProcessElectricity
from forest_ensys.schemas import ProcessElectricityCreate, ProcessElectricityUpdate


class CRUDProcessElectricity(
    CRUDBase[ProcessElectricity, ProcessElectricityCreate, ProcessElectricityUpdate]
):
    def get_from_start_date(
        self, db: Session, start_date: str
    ) -> Optional[ProcessElectricity]:
        return db.query(ProcessElectricity).filter(
            ProcessElectricity.timestamp >= start_date,
        )

    def create(
        self, db: Session, *, obj_in: ProcessElectricityCreate
    ) -> ProcessElectricity:
        obj_in_dict = obj_in.dict()
        db_obj = super().create(db, obj_in=obj_in_dict)
        return db_obj


process_electricity = CRUDProcessElectricity(ProcessElectricity)
