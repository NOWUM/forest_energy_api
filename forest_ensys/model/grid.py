# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, Integer, String, Double, DateTime
from forest_ensys.database.base_class import Base


class Grid(Base):
    """
    Grid class
    """

    timestamp = Column(DateTime, primary_key=True, nullable=False)
    commodity_id = Column(Integer, primary_key=True, nullable=False)
    commodity_name = Column(String, nullable=False)
    mwh = Column(Double, nullable=False)
    co2 = Column(Double, nullable=False)
