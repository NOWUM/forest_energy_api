# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, Double, DateTime
from forest_ensys.database.base_class import Base


class Footprint(Base):
    timestamp = Column(DateTime, primary_key=True, nullable=False)
    co2 = Column(Double, primary_key=True, nullable=False)
