# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from pydantic import BaseModel, Field


class Co2(BaseModel):
    co2: float = Field(None, description="co2 in kg_co2/kwh", example="5000")
