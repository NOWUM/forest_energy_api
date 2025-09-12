# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class EmissionsBase(BaseModel):
    """
    Shared attributes for the emissions table.
    """

    timestamp: Optional[datetime] = Field(
        default=None,
        description="Date and time when the emission factors were updated.",
        example="2020-01-01 00:00:00",
    )
    zone_key: Optional[str] = Field(
        default=None, description="Zone key of the country.", example="DE"
    )
    emission_factor_type: Optional[str] = Field(
        default=None,
        description="Emissions factor of the commodity.",
        example="direct or lifecycle",
    )
    production_mode: Optional[str] = Field(
        default=None, description="Energy commodity.", example="gas"
    )
    value: Optional[float] = Field(
        default=None, description="Emissions factor value.", example=820
    )
    source: Optional[str] = Field(
        default=None,
        description="Source of how the emissions factor is calculated.",
        example="ENTSO-E 2021",
    )


class EmissionsCreate(EmissionsBase):
    """
    Attributes to receive via API on creation of a Emissions object.
    """

    pass


class EmissionsUpdate(EmissionsBase):
    """
    Attributes to receive via API on update of a Emissions object.
    """

    pass


class EmissionsInDB(EmissionsBase):
    """
    Attributes to return via API for an Emissions object.
    """

    pass

    class Config:
        from_attributes = True


class Emissions(EmissionsInDB):
    """
    Attributes to return via API for an Emissions object.
    """

    pass
