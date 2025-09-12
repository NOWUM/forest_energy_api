# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, Double, DateTime, String
from forest_ensys.database.base_class import Base

class Prices(Base):
    timestamp = Column(DateTime, primary_key=True, nullable=False)
    source = Column(String, primary_key=True, nullable=False)
    price = Column(Double, nullable=False)