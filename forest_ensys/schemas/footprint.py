# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from pydantic import BaseModel, Field
from datetime import datetime


class Footprint(BaseModel):
    timestamp: datetime = Field(
        None, description="timestamp for every entry", example="yyyy-mm-dd hh:mm:ss"
    )
    co2: float = Field(None, description="co2 in g_co2/kwh", example="370")


class FootprintCreate(Footprint):
    pass


class FootprintUpdate(Footprint):
    pass


class FootprintInDBBase(Footprint):
    class Config:
        from_attributes = True


class Footprint(FootprintInDBBase):
    pass
