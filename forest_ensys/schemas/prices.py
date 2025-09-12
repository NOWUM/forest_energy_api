# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Prices(BaseModel):
    timestamp: Optional[datetime] = Field(
        default=None,
        description="The timestamp of the price.",
        example="2024-01-01T00:00:00",
    )
    price: Optional[float] = Field(
        default=None, description="The price in Euro.", example=0.0
    )
    source: Optional[str] = Field(
        default=None,
        description="The source of the price.",
        example="electricity_smard",
    )
