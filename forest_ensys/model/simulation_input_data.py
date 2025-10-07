# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later


from sqlalchemy import Column, Double, DateTime, String
from forest_ensys.database.base_class import Base

class SimulationInputData(Base):
    timestamp = Column(DateTime, nullable=False, primary_key=True)
    name = Column(String, nullable=False, primary_key=True)
    value = Column(Double, nullable=False)