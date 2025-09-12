# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ProcessHeatBase(BaseModel):
    """
    Base class for ProcessHeat
    """

    timestamp: datetime = Field(None, description="timestamp for every entry")
    heat_demand: float = Field(None, description="power value in watt.", example=100.0)
    # temperature: float = Field(None,
    #                             description="needed temperature for the process in C°",
    #                             example=20.0)
    # pressure: float = Field(None,
    #                         description="needed pressure for the process in Pascal",
    #                         example=300000.0)
    # mass_flow: float = Field(None,
    #                          description="needed mass flow for the process in kg/s",
    #                          example=100.0)


class ProcessHeatCreate(ProcessHeatBase):
    """
    Create a ProcessHeat entry
    """

    pass


class ProcessHeatUpdate(ProcessHeatBase):
    """
    Update a ProcessHeat entry
    """

    pass


class ProcessHeatInDBBase(ProcessHeatBase):
    """
    ProcessHeat entry to return via API
    """

    id: Optional[int] = Field(
        None, description="id of the ProcessHeat entry", example=1
    )

    ref_created_by: Optional[int] = Field(
        None, description="if of who send this heat entry", example="1"
    )

    class Config:
        from_attributes = True


class ProcessHeat(ProcessHeatInDBBase):
    pass
