# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from pydantic import BaseModel, Field
from datetime import datetime


class DataParcBase(BaseModel):
    """
    Base class for Process  entries of data parc
    """

    timestamp: datetime = Field(None, description="timestamp for every entry")
    signal_id: str = Field(
        None,
        description="uuid of the signal",
        example="123e4567-e89b-12d3-a456-426655440000",
    )
    signal_name: str = Field(
        None, description="name of the signal", example="Dampfverbrauch"
    )
    value: float = Field(None, description="value of the signal", example=100.0)
    unit: str = Field(None, description="unit of the signal", example="kWh")


class DataParcCreate(DataParcBase):
    """
    Create a Process entry
    """

    pass


class DataParcUpdate(DataParcBase):
    """
    Update a Process entry
    """

    pass


class DataParcInDBBase(DataParcBase):
    """
    Process entry to return via API
    """

    class Config:
        from_attributes = True


class DataParc(DataParcInDBBase):
    pass
