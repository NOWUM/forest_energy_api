# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter

from .endpoints import (
    grid_data,
    process_electricity_data,
    process_heat_data,
    emissions_data,
    model,
    footprint_data,
    process_data,
    flexibility,
    simulation_input_data,
    price_data,
    result_data,
)

api_router = APIRouter()
api_router.include_router(grid_data.router, prefix="/grid-data", tags=["Grid Data"])
api_router.include_router(
    emissions_data.router, prefix="/emissions-data", tags=["Emissions Data"]
)
api_router.include_router(
    footprint_data.router, prefix="/footprint-data", tags=["Footprint Data"]
)
api_router.include_router(
    flexibility.router, prefix="/flexibility", tags=["Flexibility"]
)
api_router.include_router(
    process_electricity_data.router,
    prefix="/electricity-data",
    tags=["Process Electricity Data"],
)
api_router.include_router(
    process_heat_data.router, prefix="/heat-data", tags=["Process Heat Data"]
)
api_router.include_router(model.router, prefix="/model", tags=["Model"])
api_router.include_router(process_data.router, prefix="/process-data", tags=["Process Data"])
api_router.include_router(simulation_input_data.router, prefix="/simulation-input-data", tags=["Simulation Input Data"])
api_router.include_router(price_data.router, prefix="/prices", tags=["Prices"])
api_router.include_router(result_data.router, prefix="/results", tags=["Results"])