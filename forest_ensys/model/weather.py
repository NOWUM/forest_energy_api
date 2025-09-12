# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, Integer, String, Double, DateTime
from forest_ensys.database.base_class import Base


class Weather(Base):
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False)
    nuts_id = Column(String, nullable=False)
    temperature = Column(Double, nullable=False)
    humidity = Column(Double, nullable=False)
    ghi = Column(Double, nullable=False)
