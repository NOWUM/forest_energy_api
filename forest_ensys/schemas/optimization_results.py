# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class OptimizationResult(BaseModel):
    total_energy_demand: Optional[float] = Field(
        default=None, description="The total energy demand in kWh.", example=0.0
    )
    time_from: Optional[datetime] = Field(
        default=None,
        description="The start time of the optimization.",
        example="2020-01-01 00:00:00",
    )
    time_to: Optional[datetime] = Field(
        default=None,
        description="The end time of the optimization.",
        example="2020-01-01 00:00:00",
    )
    network_fee_type: Optional[str] = Field(
        default=None,
        description="The type of network fee.",
        example="static" or "dynamic",
    )
    network_fee: Optional[float] = Field(
        default=None, description="The network fee in Euro.", example=0.0
    )
    electricity_used: Optional[float] = Field(
        default=None, description="The flexible power used in kWh.", example=0.0
    )
    gas_usage: Optional[float] = Field(
        default=None, description="The gas usage in kWh.", example=0.0
    )
    cost_savings: Optional[float] = Field(
        default=None, description="The cost savings in Euro.", example=0.0
    )
    emissions_savings: Optional[float] = Field(
        default=None, description="The emissions savings in tonnes CO2.", example=0.0
    )
    cost_gas_only: Optional[float] = Field(
        default=None, description="The cost as is in Euro for gas usage.", example=0.0
    )
    cost_with_electric_heating: Optional[float] = Field(
        default=None, description="The cost with electric heating in Euro.", example=0.0
    )
    emissions_gas_only: Optional[float] = Field(
        default=None,
        description="The emissions as is in tonnes CO2 for gas usage.",
        example=0.0,
    )
    emissions_with_electric_heating: Optional[float] = Field(
        default=None,
        description="The emissions with electric heating in tonnes CO2.",
        example=0.0,
    )
    full_load_hours: Optional[float] = Field(
        default=None, description="The full load hours.", example=0.0
    )
    full_load_hours_after_optimization: Optional[float] = Field(
        default=None, description="The full load hours after optimization.", example=0.0
    )
    mean_electricity_price_when_heating: Optional[float] = Field(
        default=None, description="The mean electricity price when heating.", example=0.0
    )
    electric_heating_in_low_price_windows_ratio: Optional[float] = Field(
        default=None,
        description="The ratio of electric heating in low price windows.",
        example=0.0,
    )

    # flexible_power_used: float
    # gas_usage: float
    # cost_savings: float
    # emissions_savings: float
