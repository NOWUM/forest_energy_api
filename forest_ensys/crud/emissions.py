# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc


from forest_ensys.crud.base import CRUDBase
from forest_ensys.model import Emissions
from forest_ensys.schemas import EmissionsCreate, EmissionsUpdate


class CRUDEmissions(CRUDBase[Emissions, EmissionsCreate, EmissionsUpdate]):
    def get_current_emissions(self, db: Session) -> Optional[Emissions]:
        latest = db.query(Emissions).order_by(desc(Emissions.timestamp)).first()
        return db.query(Emissions).filter(
            Emissions.timestamp == latest.timestamp,
            Emissions.zone_key == "DE",
            Emissions.emission_factor_type == "direct",
        )

    def get_specific_emissions(
        self, db: Session, *, zone_key: str, emission_type: str, production_mode: str
    ) -> Optional[Emissions]:
        return (
            db.query(Emissions)
            .filter(
                Emissions.zone_key == zone_key,
                Emissions.emission_factor_type == emission_type,
                Emissions.production_mode == production_mode,
            )
            .order_by(desc(Emissions.timestamp))
            .first()
        )

    def create(
        self, db: Session, obj_in=Emissions | EmissionsCreate | dict[str, any]
    ) -> Optional[Emissions]:
        new_dataset: Emissions = super().create_multi(db=db, obj_in=obj_in)
        return new_dataset

    # do a delete from emissions
    def delete(self, db: Session) -> Optional[Emissions]:
        return db.query(Emissions).delete()


emissions = CRUDEmissions(Emissions)
