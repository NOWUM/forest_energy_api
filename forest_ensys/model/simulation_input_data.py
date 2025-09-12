# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later


from sqlalchemy import Column, Integer, Double, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship

from forest_ensys.database.base_class import Base

class SimulationInputData(Base):
    timestamp = Column(DateTime, nullable=False, primary_key=True)
    ref_created_by = Column(Integer, ForeignKey("user.id"), nullable=False, primary_key=True)
    name = Column(String, nullable=False, primary_key=True)
    value = Column(Double, nullable=False)