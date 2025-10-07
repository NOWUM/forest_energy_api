# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later


from sqlalchemy import Column, Integer, Double, ForeignKey, DateTime, String

from forest_ensys.database.base_class import Base


class DataParc(Base):
    timestamp = Column(DateTime, primary_key=True, nullable=False)
    signal_id = Column(String, primary_key=True, nullable=False)
    signal_name = Column(String, nullable=False)
    value = Column(Double, nullable=False)
    unit = Column(String, nullable=False)
