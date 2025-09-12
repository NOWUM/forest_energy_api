# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import pandas as pd
from forest_ensys.crud.base import CRUDBase
from forest_ensys.model import Grid, Footprint
from forest_ensys.schemas import GridCreate, GridUpdate


class CRUDGrid(CRUDBase[Grid, GridCreate, GridUpdate]):
    def get_current_grid(self, db: Session) -> Optional[Grid]:
        latest = db.query(Grid).order_by(desc(Grid.timestamp)).first()
        return db.query(Grid).filter(Grid.timestamp == latest.timestamp)

    def get_latest_for_commodity(self, db: Session, commodity_id: int) -> pd.Timestamp:
        return (
            db.query(Grid)
            .filter(Grid.commodity_id == commodity_id)
            .order_by(desc(Grid.timestamp))
            .first()
        )

    def get_average_co2_by_commodity(self, db: Session) -> List:
        return (
            db.query(
                Grid.timestamp,
                func.sum(Grid.co2).label("total_co2"),
                func.sum(Grid.mwh).label("total_mwh"),
            )
            .outerjoin(Footprint, Grid.timestamp == Footprint.timestamp)
            .filter(Footprint.timestamp.is_(None))
            .group_by(Grid.timestamp)
            .all()
        )

    def create(self, db: Session, obj_in: Grid | dict[str, Any]) -> Optional[Grid]:
        new_dataset: Grid = super().create(db, obj_in=obj_in)
        return new_dataset
    
    def delete(self, db: Session) -> Optional[Grid]:
        return db.query(Grid).delete()


grid = CRUDGrid(Grid)
