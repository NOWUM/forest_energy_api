# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later


from sqlalchemy import Column, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from forest_ensys.database.base_class import Base


class Model(Base):
    id = Column(Integer, primary_key=True, index=True)
    model = Column(JSONB, nullable=False)
