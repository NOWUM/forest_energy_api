# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, DateTime, Float, String, Integer, ForeignKey
from forest_ensys.database.base_class import Base


class FlexiblePower(Base):
    timestamp = Column(DateTime, primary_key=True, nullable=False)
    ref_created_by = Column(
        Integer, ForeignKey("user.id"), nullable=False, primary_key=True
    )
    optimization_case_name = Column(String, primary_key=True, nullable=False)
    electricity_used = Column(Float, nullable=False)
    low_price_window = Column(Integer, nullable=False)
