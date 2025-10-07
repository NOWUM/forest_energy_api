# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, DateTime, Float, String, Integer
from forest_ensys.database.base_class import Base


class FlexiblePower(Base):
    timestamp = Column(DateTime, primary_key=True, nullable=False)
    optimization_case_name = Column(String, primary_key=True, nullable=False)
    electricity_used = Column(Float, nullable=False)
    low_price_window = Column(Integer, nullable=False)
