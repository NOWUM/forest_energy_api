# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, String, Double, DateTime
from forest_ensys.database.base_class import Base


class Emissions(Base):
    """
    Database class for the emissions of a powerplant.
    """

    timestamp = Column(DateTime, primary_key=True, nullable=False)
    zone_key = Column(String, primary_key=True, nullable=False)
    emission_factor_type = Column(String, primary_key=True, nullable=False)
    production_mode = Column(String, primary_key=True, nullable=False)
    value = Column(Double, nullable=False)
    source = Column(String, nullable=False)
