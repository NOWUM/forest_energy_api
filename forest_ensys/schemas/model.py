# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import yaml
from typing import Optional, Dict
from pydantic import BaseModel, Field

yaml_data = """
config:
  init:
    name: Wepa Mainz
    calliope_version: 0.7.0

  build:
    mode: plan # Choices: plan, operate
    ensure_feasibility: true # Switching on unmet demand

  solve:
    solver: cbc

parameters:
  objective_cost_weights:
    data: 1
    index: monetary
    dims: costs
  bigM: 1e6

data_sources:
  demand:
    source: demand_data
    rows: timesteps
    columns: [nodes, techs]
    add_dims:
      parameters: resource
    
nodes:
  X1:
    techs:
      supply_grid_power:
        cost_flow_cap.data: 100 # cost of transformers
      supply_gas:
      supply_grid_heat:
      demand_electricity:
      demand_heat:
    

techs:
  supply_grid_power:
    name: "National grid import"
    base_tech: supply
    inherit: interest_rate_setter
    carrier_out: electricity
    source_use_max: .inf
    flow_cap_max: 2000
    lifetime: 25
    cost_flow_cap:
      data: 15
      index: monetary
      dims: costs
    cost_flow_in:
      data: 0.1 # 10p/kWh electricity price #ppt
      index: monetary
      dims: costs

  supply_gas:
    name: "Natural gas import"
    base_tech: supply
    inherit: interest_rate_setter
    carrier_out: gas
    source_use_max: .inf
    flow_cap_max: 2000
    lifetime: 25
    cost_flow_cap:
      data: 1
      index: monetary
      dims: costs
    cost_flow_in:
      data: 0.025 # 2.5p/kWh gas price #ppt
      index: monetary
      dims: costs

  supply_grid_heat:
    name: "Heat from the grid"
    base_tech: supply
    carrier_out: heat
    flow_cap_max: 2000000000
    cost_flow_in:
      data: 0.05
      index: monetary
      dims: costs

  demand_electricity:
    name: "Electrical demand"
    base_tech: demand
    carrier_in: electricity

  demand_heat:
    name: "Heat demand"
    base_tech: demand
    carrier_in: heat
"""
parsed_yaml = yaml.safe_load(yaml_data)


class ModelBase(BaseModel):
    model: Optional[Dict] = Field(
        ..., description="JSON describing the technologies", example=parsed_yaml
    )


class ModelCreate(ModelBase):
    """A model representing a calliope model to be created."""

    pass


class ModelUpdate(ModelBase):
    """A model representing a calliope model to be updated."""

    pass


class ModelInDBBase(ModelBase):
    id: Optional[int] = Field(
        None, description="Unique identifier for each calliope model entry"
    )
    ref_created_by: Optional[int] = Field(
        None, description="Reference to the user who created the calliope model entry"
    )

    class Config:
        from_attributes = True


class Model(ModelInDBBase):
    """A model representing a calliope model in the database."""

    pass
