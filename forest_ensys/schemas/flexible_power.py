# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class FlexiblePowerBase(BaseModel):
    timestamp: Optional[datetime] = Field(
        default=None,
        description="Date and time when the emission factors were updated.",
        example="2020-01-01 00:00:00",
    )
    optimization_case_name: Optional[str] = Field(
        default=None,
        description="The name of the optimization case.",
        example="Optimization Case 1",
    )
    electricity_used: Optional[float] = Field(
        default=None, description="The flexible power used.", example=0.0
    )


class FlexiblePowerCreate(FlexiblePowerBase):
    pass


class FlexiblePowerUpdate(FlexiblePowerBase):
    pass


class FlexiblePowerInDB(FlexiblePowerBase):
    pass

    class Config:
        from_attributes = True


class FlexiblePower(FlexiblePowerInDB):
    pass
