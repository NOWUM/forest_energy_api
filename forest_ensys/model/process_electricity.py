# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later


from sqlalchemy import Column, Integer, Double, DateTime
from forest_ensys.database.base_class import Base


class ProcessElectricity(Base):
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False)
    power_demand = Column(Double, nullable=False)
