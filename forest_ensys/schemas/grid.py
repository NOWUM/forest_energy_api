# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from pydantic import BaseModel, Field
from datetime import datetime


class GridBase(BaseModel):
    """
    Shared attributes for the grid table.
    """

    timestamp: datetime = Field(
        None, description="timestamp for every entry", example="yyyy-mm-dd hh:mm:ss"
    )
    mwh: float = Field(None, description="power value in mwh.", example="5000")
    commodity_id: int = Field(None, description="id of the energy type", example="4067")
    commodity_name: str = Field(
        None, description="name of the energy type", example="Wind Onshore"
    )
    co2: float = Field(None, description="co2 in kg_co2/kwh", example="5000")


class GridCreate(GridBase):
    """
    Attributes to receive via API on creation of a dataset.
    """

    pass


class GridUpdate(GridBase):
    """
    Attributes to receive via API on update of a dataset.
    """

    pass


class GridInDBBase(GridBase):
    class Config:
        from_attributes = True


class Grid(GridInDBBase):
    """
    Attributes to return via API for a dataset.
    """

    pass
