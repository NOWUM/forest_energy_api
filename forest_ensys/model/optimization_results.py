# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, Float, String, Integer, ForeignKey, DateTime
from forest_ensys.database.base_class import Base


class OptimizationResult(Base):
    name = Column(String, nullable=False, primary_key=True)
    ref_created_by = Column(
        Integer, ForeignKey("user.id"), nullable=False, primary_key=True
    )
    time_from = Column(DateTime, nullable=False)
    time_to = Column(DateTime, nullable=False)
    network_fee_type = Column(String, nullable=False)
    network_fee = Column(Float, nullable=False)
    total_energy_demand = Column(Float, nullable=False)
    electricity_used = Column(Float, nullable=False)
    gas_usage = Column(Float, nullable=False)
    cost_savings = Column(Float, nullable=False)
    emissions_savings = Column(Float, nullable=False)
    cost_gas_only = Column(Float, nullable=False)
    cost_with_electric_heating = Column(Float, nullable=False)
    emissions_gas_only = Column(Float, nullable=False)
    emissions_with_electric_heating = Column(Float, nullable=False)
    full_load_hours = Column(Float, nullable=False)
    full_load_hours_after_optimization = Column(Float, nullable=False)
    mean_electricity_price_when_heating = Column(Float, nullable=False)
    electric_heating_in_low_price_windows_ratio = Column(Float, nullable=False)
