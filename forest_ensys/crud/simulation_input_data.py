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
        self, db: Session, *, obj_in: SimulationInputData, user_id: int
    ) -> SimulationInputData:
        obj_in_dict = obj_in.dict()
        obj_in_dict["ref_created_by"] = user_id
        db_obj = super().create(db, obj_in=obj_in_dict)
        return db_obj
    def delete_by_user_and_name(self, db: Session, *, user_id: int, name: str) -> Optional[SimulationInputData]:
        return db.query(self.model).filter(self.model.ref_created_by == user_id, self.model.name == name).delete()
    def get_multi_by_date_range_and_name(
        self, db: Session, *, start_date: datetime, end_date: datetime,user_id: int, name: str
    ) -> Optional[pd.DataFrame]:
        query = """
            SELECT * 
            FROM simulation_input_data
            WHERE timestamp BETWEEN :start_date AND :end_date AND ref_created_by = :user_id AND name = :name
        """

        # Abfrage ausführen
        result = pd.read_sql_query(
            sql=text(query),
            con=db.connection(),
            params={
                "start_date": start_date,
                "end_date": end_date,
                "name": name,
                "user_id": user_id
            },
        )

        return result if not result.empty else None
    
simulation_input_data = CRUDSimulationInputData(SimulationInputData)