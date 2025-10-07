# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from sqlalchemy.orm import Session
from forest_ensys.crud.base import CRUDBase
from forest_ensys.model import DataParc
from forest_ensys.schemas import DataParcCreate, DataParcUpdate


class CRUDDataParc(CRUDBase[DataParc, DataParcCreate, DataParcUpdate]):
    def create(self, db: Session, *, obj_in: DataParcCreate) -> DataParc:
        obj_in_dict = obj_in.dict()
        db_obj = super().create(db, obj_in=obj_in_dict)
        return db_obj

    def delete(self, db: Session) -> Optional[DataParc]:
        return db.query(DataParc).delete()


data_parc = CRUDDataParc(DataParc)
