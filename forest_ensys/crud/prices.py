# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy import text
from forest_ensys.crud.base import CRUDBase
from forest_ensys.model import Prices
from datetime import datetime
import pandas as pd


class CRUDPrices(CRUDBase[Prices, Any, Any]):
    def get_by_timestamp(self, db: Session, *, timestamp: Any) -> Optional[Prices]:
        return db.query(Prices).filter(Prices.timestamp == timestamp).first()

    def get_latest(self, db: Session) -> Optional[Prices]:
        return (
            db.query(Prices)
            .filter(Prices.source == "smard")
            .order_by(desc(Prices.timestamp))
            .first()
        )

    def get_by_timestamp_range(
        self, db: Session, *, start: Any, end: Any
    ) -> List[Prices]:
        return (
            db.query(Prices)
            .filter(Prices.timestamp >= start, Prices.timestamp <= end)
            .all()
        )

    def get_by_source(
        self, db: Session, *, source: str, limit: int = 100, skip: int = 0
    ) -> List[Prices]:
        return (
            db.query(Prices)
            .filter(Prices.source == source)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_multi_by_date_range_and_source(
        self, db: Session, *, start_date: datetime, end_date: datetime, source: str
    ) -> Optional[pd.DataFrame]:
        query = """
            SELECT * 
            FROM prices
            WHERE timestamp BETWEEN :start_date AND :end_date AND source = :source
        """

        # Abfrage ausführen
        result = pd.read_sql_query(
            sql=text(query),
            con=db.connection(),
            params={
                "start_date": start_date,
                "end_date": end_date,
                "source": source,
            },
        )

        return result if not result.empty else None

    def create(self, db: Session, obj_in: Prices | dict[str, Any]) -> Optional[Prices]:
        new_dataset: Prices = super().create(db, obj_in=obj_in)
        return new_dataset

    def delete(self, db: Session, source: str) -> Optional[Prices]:
        return db.query(Prices).filter(Prices.source == source).delete()

    def get_distinct_names(self, db: Session) -> list[str]:
        rows = db.query(self.model.source).distinct().order_by(self.model.source).all()
        return [r[0] for r in rows]


prices = CRUDPrices(Prices)
