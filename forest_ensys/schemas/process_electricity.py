# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from pydantic import BaseModel, Field
from datetime import datetime


class ProcessElectricityBase(BaseModel):
    timestamp: datetime = Field(
        ...,
        description="timestamp for every entry",
    )
    power_demand: float = Field(..., description="power value in watt.", example="5000")


class ProcessElectricityCreate(ProcessElectricityBase):
    pass


class ProcessElectricityUpdate(ProcessElectricityBase):
    pass


class ProcessElectricityInDBBase(ProcessElectricityBase):
    id: int = Field(
        ...,
        description="id for every entry",
    )

    class Config:
        from_attributes = True


class ProcessElectricity(ProcessElectricityInDBBase):
    pass
