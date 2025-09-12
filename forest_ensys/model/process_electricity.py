# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later


from sqlalchemy import Column, Integer, Double, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from forest_ensys.database.base_class import Base


class ProcessElectricity(Base):
    id = Column(Integer, primary_key=True, index=True)
    ref_created_by = Column(Integer, ForeignKey("user.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    power_demand = Column(Double, nullable=False)

    user = relationship("User", back_populates="process_electricity")
