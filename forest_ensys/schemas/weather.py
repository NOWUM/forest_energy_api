# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class WeatherBase(BaseModel):
    timestamp: datetime = Field(
        None, description="timestamp for every entry", example="yyyy-mm-dd hh:mm:ss"
    )
    nuts_id: str = Field(None, description="nuts id", example="DE")
    temperature: float = Field(
        None, description="temperature in celsius.", example=25.0
    )
    humidity: float = Field(None, description="humidity in percentage.", example=50.0)
    ghi: float = Field(
        None, description="global horizontal irradiation in w/m2.", example=100.0
    )


class WeatherCreate(WeatherBase):
    pass


class WeatherUpdate(WeatherBase):
    pass


class WeatherInDBBase(WeatherBase):
    id: Optional[int] = None

    class Config:
        from_attributes = True


class Weather(WeatherInDBBase):
    pass
