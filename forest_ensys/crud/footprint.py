# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from forest_ensys.crud.base import CRUDBase
from forest_ensys.model import Footprint
from forest_ensys.schemas import FootprintCreate, FootprintUpdate


class CRUDFootprint(CRUDBase[Footprint, FootprintCreate, FootprintUpdate]):
    def get_latest(self, db: Session) -> Optional[Footprint]:
        return db.query(Footprint).order_by(desc(Footprint.timestamp)).first()

    def create(self, db: Session, *, obj_in: FootprintCreate) -> Optional[Footprint]:
        new_dataset: Footprint = super().create(db, obj_in=obj_in)
        return new_dataset

    # def get_multi_by_date_range(self,db: Session, start_date: datetime, end_date: datetime):
    #     return db.query(Footprint).filter(Footprint.timestamp >= start_date, Footprint.timestamp <= end_date).all()
    def delete(self, db: Session) -> Optional[Footprint]:
        return db.query(Footprint).delete()


footprint = CRUDFootprint(Footprint)
