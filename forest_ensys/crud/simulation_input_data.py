# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional, Any

from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from forest_ensys.crud.base import CRUDBase
from forest_ensys.model import SimulationInputData
from datetime import datetime
import pandas as pd


class CRUDSimulationInputData(CRUDBase[SimulationInputData, Any, Any]):
    def create(
        self, db: Session, *, obj_in: SimulationInputData
    ) -> SimulationInputData:
        obj_in_dict = obj_in.dict()
        db_obj = super().create(db, obj_in=obj_in_dict)
        return db_obj

    def delete_by_name(
        self, db: Session, *, name: str
    ) -> Optional[SimulationInputData]:
        return db.query(self.model).filter(self.model.name == name).delete()

    def get_multi_by_date_range_and_name(
        self, db: Session, *, start_date: datetime, end_date: datetime, name: str
    ) -> Optional[pd.DataFrame]:
        query = """
            SELECT * 
            FROM simulation_input_data
            WHERE timestamp BETWEEN :start_date AND :end_date AND  name = :name
        """

        # Abfrage ausführen
        result = pd.read_sql_query(
            sql=text(query),
            con=db.connection(),
            params={"start_date": start_date, "end_date": end_date, "name": name},
        )

        return result if not result.empty else None
    
    def get_distinct_names(self, db: Session) -> list[str]:
        rows = db.query(self.model.name).distinct().order_by(self.model.name).all()
        return [r[0] for r in rows]


simulation_input_data = CRUDSimulationInputData(SimulationInputData)
