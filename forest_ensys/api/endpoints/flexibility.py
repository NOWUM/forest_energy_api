# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Text
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from forest_ensys import crud, model, schemas
from forest_ensys.api import deps
from forest_ensys.core.timeseries_helpers import (
    check_granularity_and_merge,
    calculate_dynamic_network_fee,
)
from forest_ensys.core.optimization import optimize_dryers as optimize
from forest_ensys.core.aas_helper import get_data_from_aas
from datetime import datetime

import pandas as pd
import numpy as np

router = APIRouter()


@router.delete(
    "/",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Flexibility data table deleted successfully",
                    }
                }
            }
        }
    },
)
def delete_flexibility_data(
    db: Session = Depends(deps.get_db),
    current: model.User = Depends(deps.get_current_user),
) -> Text:
    """
    Delete all flexibility data
    """
    crud.flexible_power.delete(db=db, user_id=current.id)
    crud.optimization_results.delete(db=db, user_id=current.id)
    raise HTTPException(
        status_code=200, detail="Flexibility data table deleted successfully"
    )


@router.delete(
    "/{optimization_case_name}",
    responses={200: {"description": "Optimization case deleted successfully"}},
)
def delete_optimization_case(
    optimization_case_name: str,
    db: Session = Depends(deps.get_db),
    current: model.User = Depends(deps.get_current_user),
) -> Text:
    """
    Delete a specific optimization case
    """
    crud.flexible_power.delete_by_user_id_and_optimization_case_name(
        db=db, user_id=current.id, optimization_case_name=optimization_case_name
    )
    crud.optimization_results.delete_by_user_id_and_optimization_case_name(
        db=db, user_id=current.id, optimization_case_name=optimization_case_name
    )
    raise HTTPException(
        status_code=200, detail="Optimization case deleted successfully"
    )


@router.post(
    "/optimize_flexibility",
    response_model=schemas.OptimizationResult,
    responses={404: {"description": "No data found for the given date range"}},
)
def optimize_flexibility(
    db: Session = Depends(deps.get_db),
    current: model.User = Depends(deps.get_current_user),
    start_date: datetime = "2024-10-01",
    end_date: datetime = "2024-10-31",
    flexible_power: float = 8000,  # kW
    electricity_network_fee: float = 10,  # cost per MWh
    gas_emissions_factor: float = 204,  # g/kWh
    cost_per_mwh_gas: float = 60,  # cost per MWh
    co2_price: float = 55,  # cost per ton of CO2
) -> schemas.OptimizationResult:
    """
    Binary decision problem to optimize the use of electric heating
    """
    crud.flexible_power.delete_by_user_id_and_optimization_case_name(
        db=db, user_id=current.id, optimization_case_name="binary_decision_problem"
    )
    crud.optimization_results.delete_by_user_id_and_optimization_case_name(
        db=db, user_id=current.id, optimization_case_name="binary_decision_problem"
    )
    # Retrieve data from database
    footprint_data = crud.footprint.get_multi_by_date_range(
        db=db, start_date=start_date, end_date=end_date
    )
    heat_demand = crud.data_parc.get_multi_by_date_range(
        db=db, user_id=current.id, start_date=start_date, end_date=end_date
    )
    price_data = crud.prices.get_multi_by_date_range_and_source(
        db=db,
        start_date=start_date,
        end_date=end_date,
        source="smard",
    )

    # Merge dataframes and check granularity
    merged_data = check_granularity_and_merge(
        footprint_data, heat_demand[["timestamp", "value"]], method="sum"
    )
    merged_data = check_granularity_and_merge(
        merged_data,
        price_data[["timestamp", "price"]].rename(
            columns={"price": "electricity_price"}
        ),
    )
    merged_data["electricity_price"] = (
        merged_data["electricity_price"] + electricity_network_fee
    )

    time_interval_hours = merged_data["timestamp"].diff().min().total_seconds() / 3600

    # Decision based on electrical power (kW) at each timestamp
    use_flexible_power = merged_data["co2"] < gas_emissions_factor
    total_energy_demand = merged_data["value"].sum()
    # Integrate flexible power used and gas usage over time (kWh)
    electricity_used = np.where(
        use_flexible_power, flexible_power * time_interval_hours, 0
    ).sum()
    gas_usage = total_energy_demand - electricity_used

    # Flexible power time series (kWh per interval)
    flexible_power_time_series = pd.DataFrame(
        {
            "timestamp": merged_data["timestamp"],
            "electricity_used": np.where(use_flexible_power, flexible_power, 0),
        }
    )

    emissions_gas_only = merged_data["value"].sum() * gas_emissions_factor * 1e-6

    emissions_savings = (
        np.where(
            use_flexible_power,
            (gas_emissions_factor - merged_data["co2"])
            * flexible_power
            * time_interval_hours,
            0,
        ).sum()
    ) * 1e-6  # convert to tonnes

    emissions_with_electric_heating = emissions_gas_only - emissions_savings

    cost_gas_only = (
        total_energy_demand * 1e-3 * cost_per_mwh_gas
        + emissions_gas_only * 1e-6 * co2_price
    )

    cost_savings = emissions_savings * co2_price + (
        np.where(
            use_flexible_power,
            (cost_per_mwh_gas - merged_data["electricity_price"])
            * flexible_power
            * time_interval_hours
            * 1e-3,
            0,
        ).sum()
    )

    cost_with_electric_heating = cost_gas_only - cost_savings

    flexible_power = pd.DataFrame(
        {
            "timestamp": flexible_power_time_series["timestamp"],
            "electricity_used": flexible_power_time_series["electricity_used"],
            "low_price_window": 0,
            "optimization_case_name": "binary_decision_problem",
            "ref_created_by": current.id,
        }
    )

    crud.flexible_power.create_multi(
        db=db, obj_in=flexible_power.to_dict(orient="records")
    )

    optimization_results = {
        "name": "binary_decision_problem",
        "ref_created_by": current.id,
        "time_from": start_date,
        "time_to": end_date,
        "network_fee_type": "static",
        "network_fee": 0.0,
        "total_energy_demand": round(total_energy_demand, 2),
        "electricity_used": round(electricity_used, 2),
        "gas_usage": round(gas_usage, 2),
        "cost_savings": round(cost_savings, 2),
        "emissions_savings": round(emissions_savings, 2),
        "cost_gas_only": round(cost_gas_only, 2),
        "cost_with_electric_heating": round(cost_with_electric_heating, 2),
        "emissions_gas_only": round(emissions_gas_only, 2),
        "emissions_with_electric_heating": round(emissions_with_electric_heating, 2),
        "full_load_hours": 0,
        "full_load_hours_after_optimization": 0,
        "mean_electricity_price_when_heating": (
            merged_data["electricity_price"][use_flexible_power].mean()
        ),
        "electric_heating_in_low_price_windows_ratio": 0,
    }

    return crud.optimization_results.create(db=db, obj_in=optimization_results)


@router.post(
    "/optimize_flexibility_aas",
    response_model=schemas.OptimizationResult,
    responses={404: {"description": "No data found for the given date range"}},
)
def optimize_flexibility_aas_data(
    db: Session = Depends(deps.get_db),
    current: model.User = Depends(deps.get_current_user),
) -> schemas.OptimizationResult:
    """
    Binary decision problem to optimize the use of electric heating
    """
    parameters = get_data_from_aas()
    crud.flexible_power.delete_by_user_id_and_optimization_case_name(
        db=db, user_id=current.id, optimization_case_name="binary_decision_problem"
    )
    flexible_power = int(parameters["powerMax"])
    electricity_network_fee = int(parameters["electricityNetworkFee"])
    gas_emissions_factor = 204
    cost_per_mwh_gas = int(parameters["gasPrice"])
    co2_price = int(parameters["co2Price"])
    crud.optimization_results.delete_by_user_id_and_optimization_case_name(
        db=db, user_id=current.id, optimization_case_name="binary_decision_problem"
    )
    # Retrieve data from database
    footprint_data = crud.footprint.get_multi_by_date_range(
        db=db, start_date=parameters["from"], end_date=parameters["until"]
    )
    heat_demand = crud.data_parc.get_multi_by_date_range(
        db=db,
        user_id=current.id,
        start_date=parameters["from"],
        end_date=parameters["until"],
    )
    price_data = crud.prices.get_multi_by_date_range_and_source(
        db=db,
        start_date=parameters["from"],
        end_date=parameters["until"],
        source="smard",
    )

    # Merge dataframes and check granularity
    merged_data = check_granularity_and_merge(
        footprint_data, heat_demand[["timestamp", "value"]], method="sum"
    )
    merged_data = check_granularity_and_merge(
        merged_data,
        price_data[["timestamp", "price"]].rename(
            columns={"price": "electricity_price"}
        ),
    )
    merged_data["electricity_price"] = (
        merged_data["electricity_price"] + electricity_network_fee
    )

    time_interval_hours = merged_data["timestamp"].diff().min().total_seconds() / 3600

    # Decision based on electrical power (kW) at each timestamp
    use_flexible_power = merged_data["co2"] < gas_emissions_factor
    total_energy_demand = merged_data["value"].sum()
    # Integrate flexible power used and gas usage over time (kWh)
    electricity_used = np.where(
        use_flexible_power, flexible_power * time_interval_hours, 0
    ).sum()
    gas_usage = total_energy_demand - electricity_used

    # Flexible power time series (kWh per interval)
    flexible_power_time_series = pd.DataFrame(
        {
            "timestamp": merged_data["timestamp"],
            "electricity_used": np.where(use_flexible_power, flexible_power, 0),
        }
    )

    emissions_gas_only = merged_data["value"].sum() * gas_emissions_factor * 1e-6

    emissions_savings = (
        np.where(
            use_flexible_power,
            (gas_emissions_factor - merged_data["co2"])
            * flexible_power
            * time_interval_hours,
            0,
        ).sum()
    ) * 1e-6  # convert to tonnes

    emissions_with_electric_heating = emissions_gas_only - emissions_savings

    cost_gas_only = (
        total_energy_demand * 1e-3 * cost_per_mwh_gas
        + emissions_gas_only * 1e-6 * co2_price
    )

    cost_savings = emissions_savings * co2_price + (
        np.where(
            use_flexible_power,
            (cost_per_mwh_gas - merged_data["electricity_price"])
            * flexible_power
            * time_interval_hours
            * 1e-3,
            0,
        ).sum()
    )

    cost_with_electric_heating = cost_gas_only - cost_savings

    flexible_power = pd.DataFrame(
        {
            "timestamp": flexible_power_time_series["timestamp"],
            "electricity_used": flexible_power_time_series["electricity_used"],
            "low_price_window": 0,
            "optimization_case_name": "binary_decision_problem",
            "ref_created_by": current.id,
        }
    )

    crud.flexible_power.create_multi(
        db=db, obj_in=flexible_power.to_dict(orient="records")
    )

    optimization_results = {
        "name": "binary_decision_problem",
        "ref_created_by": current.id,
        "time_from": parameters["from"],
        "time_to": parameters["until"],
        "network_fee_type": "static",
        "network_fee": 0.0,
        "total_energy_demand": round(total_energy_demand, 2),
        "electricity_used": round(electricity_used, 2),
        "gas_usage": round(gas_usage, 2),
        "cost_savings": round(cost_savings, 2),
        "emissions_savings": round(emissions_savings, 2),
        "cost_gas_only": round(cost_gas_only, 2),
        "cost_with_electric_heating": round(cost_with_electric_heating, 2),
        "emissions_gas_only": round(emissions_gas_only, 2),
        "emissions_with_electric_heating": round(emissions_with_electric_heating, 2),
        "full_load_hours": 0,
        "full_load_hours_after_optimization": 0,
        "mean_electricity_price_when_heating": (
            merged_data["electricity_price"][use_flexible_power].mean()
        ),
        "electric_heating_in_low_price_windows_ratio": 0,
    }

    return crud.optimization_results.create(db=db, obj_in=optimization_results)


@router.post(
    "/optimize_dryers",
    response_model=schemas.OptimizationResult,
    responses={
        404: {"description": "No data found for the given date range"},
        400: {"description": "Invalid Network Type"},
        501: {"description": "Not implemented yet"},
        500: {"description": "Internal Server Error"},
        401: {"description": "Unauthorized"},
    },
)
def optimize_dryers(
    db: Session = Depends(deps.get_db),
    current: model.User = Depends(deps.get_current_user),
    start_date: datetime = Query(
        "2024-01-01", description="Start date for the optimization period."
    ),
    end_date: datetime = Query(
        "2024-12-31", description="End date for the optimization period."
    ),
    optimization_case_name: str = Query(
        "optimization_case_1",
        description="Name of the optimization case. Used to store the results in the database.",
    ),
    electricity_price_data_source: str = Query(
        "smard",
        description="Data source for electricity prices. Smard are the market prices. You can upload PFCs or other forecasts under prices.",
    ),
    gas_price_data_source: str = Query(
        "gas_spot",
        description="Data source for gas prices. Constant uses a constant gas price for the whole period. You can upload PFCs or other forecasts under prices.",
    ),
    flexible_power: int = Query(
        8000, description="The power of the flexible load in kW."
    ),
    gas_emissions_factor: int = Query(
        204,
        description="The emissions factor for gas in g/kWh. It is around 200g/kWh for natural gas based on the Gross Calorific Value.",
    ),
    cost_per_mwh_gas: int = Query(
        60,
        description="The cost of gas in €/MWh. 60€/MWh was the average price for gas in Germany in 2024.",
    ),
    co2_price: int = Query(
        55,
        description="The price of CO2 in €/Tonne CO2. 55€/Tonne is the price for CO2 in Germany in 2025.",
    ),
    ramp_up_rate: int = Query(
        6000, description="The ramp up rate of the flexible load in kW/h."
    ),
    ramp_down_rate: int = Query(
        6000, description="The ramp down rate of the flexible load in kW/h."
    ),
    minimum_runtime: int = Query(
        2, description="The minimum runtime of the flexible load in quarter hours."
    ),
    network_fee: str = Query(
        "static",
        enum=["static", "dynamic"],
        description="Method for calculating network fees. Static adds a fixed value to the market electricity price, while dynamic calculates the network fee based on BK4-22-089",
    ),
    network_fee_value: float = Query(
        20.0,
        description="The network fee value in €/MWh.",
    ),
    relative_network_fee_reduction: float = Query(
        0.8,
        description="The relative reduction of the network fee for flexible loads.",
    ),
    gas_network_fee: float = Query(
        4.0,
        description="The gas network fee in €/MWh.",
    ),
    relative_network_fee_surcharge: float = Query(
        0.1,
        description="The relative surcharge of the network fee for inflexible loads.",
    ),
    window_size: int = Query(
        2,
        description="The window size for the dynamic network fee calculation in hours.",
    ),
) -> schemas.OptimizationResult:
    """
    Optimizes the use of electric heating using Pyomo.
    """
    if start_date > end_date:
        raise HTTPException(
            status_code=400, detail="Start date must be before end date"
        )
    if any(
        value < 0 or not isinstance(value, (int, float)) or value is None
        for value in [
            flexible_power,
            gas_emissions_factor,
            cost_per_mwh_gas,
            co2_price,
            ramp_up_rate,
            ramp_down_rate,
            minimum_runtime,
            network_fee_value,
        ]
    ):
        raise HTTPException(
            status_code=400, detail="All values must be positive numbers"
        )
    if (
        crud.optimization_results.get(
            db=db, user_id=current.id, optimization_case_name=optimization_case_name
        )
        is not None
    ):
        raise HTTPException(
            status_code=400,
            detail="Optimization case already exists. Please delete it first or change the name.",
        )
    footprint_data = crud.footprint.get_multi_by_date_range(
        db=db, start_date=start_date, end_date=end_date
    )
    if footprint_data is None:
        raise HTTPException(
            status_code=404, detail="No footprint data found for the given date range"
        )
    heat_demand = crud.simulation_input_data.get_multi_by_date_range_and_name(
        db=db,
        user_id=current.id,
        start_date=start_date,
        end_date=end_date,
        name="flexible_device_demand",
    )
    if heat_demand is None:
        raise HTTPException(
            status_code=404, detail="No heat demand data found for the given date range"
        )
    heat_demand.rename(columns={"value": heat_demand["name"][0]}, inplace=True)
    heat_demand.drop(columns=["name"], inplace=True)
    total_electricity_demand = (
        crud.simulation_input_data.get_multi_by_date_range_and_name(
            db=db,
            user_id=current.id,
            start_date=start_date,
            end_date=end_date,
            name="total_electricity_demand",
        )
    )
    if total_electricity_demand is None:
        raise HTTPException(
            status_code=404,
            detail="No total electricity demand data found for the given date range",
        )
    total_electricity_demand.rename(
        columns={"value": total_electricity_demand["name"][0]}, inplace=True
    )
    total_electricity_demand.drop(columns=["name"], inplace=True)
    electricity_price_data = crud.prices.get_multi_by_date_range_and_source(
        db=db,
        start_date=start_date,
        end_date=end_date,
        source=electricity_price_data_source,
    )
    if electricity_price_data is None:
        raise HTTPException(
            status_code=404,
            detail="No price data found for the given date range and source",
        )
    if gas_price_data_source != "constant":
        gas_price_data = crud.prices.get_multi_by_date_range_and_source(
            db=db,
            start_date=start_date,
            end_date=end_date,
            source=gas_price_data_source,
        )
        if gas_price_data is None:
            raise HTTPException(
                status_code=404,
                detail="No gas price data found for the given date range and source",
            )
        # as gas price data is only daily data, we interpolate it to 15 minutes
        gas_price_data = (
            gas_price_data.set_index("timestamp")
            .resample("15min")
            .ffill()
            .reset_index()
        )
    else:
        gas_price_data = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    start=start_date, end=end_date, freq="15min"
                ),
                "price": cost_per_mwh_gas,
                "source": "constant",
            }
        )

    # Merge dataframes and check granularity
    merged_data = check_granularity_and_merge(footprint_data, heat_demand, method="sum")
    merged_data = check_granularity_and_merge(
        merged_data, total_electricity_demand, method="sum"
    )
    merged_data = check_granularity_and_merge(
        merged_data,
        electricity_price_data[["timestamp", "price"]].rename(
            columns={"price": "electricity_price"}
        ),
    )  # TODO make this better
    merged_data = check_granularity_and_merge(
        merged_data,
        gas_price_data[["timestamp", "price"]].rename(columns={"price": "gas_price"}),
    )
    merged_data["gas_data_source"] = gas_price_data["source"]
    merged_data["electricity_data_source"] = electricity_price_data["source"]

    if merged_data.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found for the given date range",
        )

    if merged_data["timestamp"][0] != pd.to_datetime(start_date).tz_localize(
        "UTC"
    ) or merged_data["timestamp"].iloc[-1] != pd.to_datetime(end_date).tz_localize(
        "UTC"
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data does not cover the entire date range",
        )
    # we can also make full load hours a parameter. Then we would not need the time series anymore.
    granularity_factor = 1 / (
        merged_data["timestamp"].diff().min().total_seconds() / 3600
    )
    full_load_hours = merged_data["total_electricity_demand"].sum() / (
        merged_data["total_electricity_demand"].max() * granularity_factor
    )

    if network_fee == "static":
        merged_data["electricity_price"] = merged_data[
            "electricity_price"
        ] + network_fee_value * (1 - relative_network_fee_reduction)
        merged_data["window_type"] = 0
    elif network_fee == "dynamic":
        merged_data = calculate_dynamic_network_fee(
            merged_data,
            network_fee_value,
            relative_network_fee_reduction,
            relative_network_fee_surcharge,
            window_size,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid network fee type",
        )
    merged_data["gas_price"] = merged_data["gas_price"] + gas_network_fee

    # Parameters
    heat_demand_dict = merged_data[
        "flexible_device_demand"
    ].to_dict()  # Heat demand per interval (kW)
    co2_electricity_dict = merged_data[
        "co2"
    ].to_dict()  # Electricity CO2 intensity (g/kWh)
    price_electricity_dict = merged_data[
        "electricity_price"
    ].to_dict()  # Electricity price (€/MWh)
    price_gas_dict = merged_data["gas_price"].to_dict()  # Gas price (€/MWh)
    electricity_demand = merged_data["total_electricity_demand"].to_dict()
    window_type = merged_data["window_type"].to_dict()

    time_interval_hours = merged_data["timestamp"].diff().min().total_seconds() / 3600

    optimization_results = optimize(
        co2_data=co2_electricity_dict,
        heat_demand_data=heat_demand_dict,
        electricity_price_data=price_electricity_dict,
        electricity_demand=electricity_demand,
        window_type=window_type,
        electric_heating=flexible_power,
        gas_emissions_factor=gas_emissions_factor,
        gas_price_data=price_gas_dict,
        co2_price=co2_price,
        ramp_up_rate=ramp_up_rate,
        ramp_down_rate=ramp_down_rate,
        minimum_runtime=minimum_runtime,
        time_interval_hours=time_interval_hours,
    )

    merged_data["total_electricity_demand_with_flexible_power"] = np.where(
        merged_data["window_type"] != 1,
        merged_data["total_electricity_demand"]
        + (
            optimization_results["optimized_results_df"]["electric_power_used_kW"]
            * time_interval_hours
        ),
        merged_data["total_electricity_demand"],
    )
    full_load_hours_after_optimization = merged_data[
        "total_electricity_demand_with_flexible_power"
    ].sum() / (
        merged_data["total_electricity_demand_with_flexible_power"].max()
        * granularity_factor
    )
    print("Full Load Hours After Optimization: ", full_load_hours_after_optimization)

    electric_heating_in_low_price_windows = merged_data[
        merged_data["window_type"] == 1
    ]["total_electricity_demand_with_flexible_power"].sum()
    electric_heating_in_low_price_windows_ratio = (
        electric_heating_in_low_price_windows
        / (merged_data["total_electricity_demand_with_flexible_power"].sum())
    )
    mean_electricity_price_when_heating = np.nanmean(
        np.where(
            optimization_results["optimized_results_df"]["electric_power_used_kW"] > 0,
            merged_data["electricity_price"],
            np.nan,
        )
    )
    # Store optimized electric power usage in DB if needed:
    optimization_results["optimized_results_df"]["timestamp"] = merged_data["timestamp"]
    flexible_power = pd.DataFrame(
        {
            "timestamp": merged_data["timestamp"],
            "electricity_used": optimization_results["optimized_results_df"][
                "electric_power_used_kW"
            ],
            "low_price_window": merged_data["window_type"],
            "optimization_case_name": optimization_case_name,
            "ref_created_by": current.id,
        }
    )

    optimization_results["name"] = optimization_case_name
    optimization_results["time_from"] = start_date
    optimization_results["time_to"] = end_date
    optimization_results["network_fee_type"] = network_fee
    optimization_results["network_fee"] = network_fee_value
    optimization_results["full_load_hours"] = full_load_hours
    optimization_results["full_load_hours_after_optimization"] = (
        full_load_hours_after_optimization
    )
    optimization_results["mean_electricity_price_when_heating"] = round(
        mean_electricity_price_when_heating, 2
    )
    optimization_results["electric_heating_in_low_price_windows_ratio"] = round(
        electric_heating_in_low_price_windows_ratio, 2
    )
    try:
        crud.flexible_power.create_multi(
            db=db, obj_in=flexible_power.to_dict(orient="records")
        )
        return crud.optimization_results.create(
            db=db, obj_in=optimization_results, user_id=current.id
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# @router.post("/optimize_flexible_power_size", response_model=schemas.OptimizationResult)
# def optimize_flexible_power_size(
#     db: Session = Depends(deps.get_db),
#     current: model.User = Depends(deps.get_current_user),
#     start_date: datetime = "2024-09-10",
#     end_date: datetime = "2024-09-28",
#     max_flexible_power: float = 100000,
#     flexible_power_cost: float = 0.00001,
#     gas_emissions_factor: float = 800,
#     gas_price: float = 0.1,
#     w_cost: float = 0.5,
#     w_emissions: float = 0.5,
# ) -> schemas.OptimizationResult:
#     # Validate weights
#     if not (0 <= w_cost <= 1) or not (0 <= w_emissions <= 1):
#         raise HTTPException(status_code=400, detail="Weights must be between 0 and 1.")

#     if abs(w_cost + w_emissions - 1) > 1e-6:
#         raise HTTPException(
#             status_code=400, detail="The sum of w_cost and w_emissions must equal 1."
#         )

#     # Retrieve data from database
#     footprint_data = crud.footprint.get_multi_by_date_range(
#         db=db, start_date=start_date, end_date=end_date
#     )
#     heat_demand = crud.data_parc.get_multi_by_date_range(
#         db=db, user_id=current.id, start_date=start_date, end_date=end_date
#     )
#     price_data = crud.prices.get_multi_by_date_range(
#         db=db, start_date=start_date, end_date=end_date
#     )

#     # Merge dataframes and check granularity
#     merged_data = check_granularity_and_merge(footprint_data, heat_demand)
#     merged_data = check_granularity_and_merge(merged_data, price_data)

#     # Extract relevant data from the dataframes
#     co2_emissions = merged_data["co2"].values.tolist()
#     heat_demand_values = merged_data["value"].values.tolist()
#     timestamps = merged_data["timestamp"].values

#     el_price = merged_data["price"].tolist()

#     # Create Pyomo model
#     model = ConcreteModel()

#     # Define sets (time steps)
#     model.T = RangeSet(0, len(timestamps) - 1)

#     # Parameters
#     model.co2_emissions = Param(
#         model.T, initialize={i: co2_emissions[i] for i in range(len(co2_emissions))}
#     )
#     model.heat_demand = Param(
#         model.T,
#         initialize={i: heat_demand_values[i] for i in range(len(heat_demand_values))},
#     )
#     model.el_price = Param(
#         model.T, initialize={i: el_price[i] for i in range(len(el_price))}
#     )

#     # Decision variable: Single flexible power variable for the entire time period
#     model.flexible_power = Var(within=NonNegativeReals, bounds=(0, max_flexible_power))
#     model.gas_power = Var(model.T, within=NonNegativeReals)

#     # Objective function with normalization
#     def objective_rule(model):
#         max_cost = max(el_price) * max_flexible_power * len(
#             heat_demand_values
#         ) + gas_price * sum(heat_demand_values)
#         max_emission = gas_emissions_factor * sum(heat_demand_values)

#         normalized_cost = sum(
#             (model.el_price[t] * model.flexible_power + gas_price * model.gas_power[t])
#             / max_cost
#             for t in model.T
#         )

#         normalized_emission = sum(
#             (
#                 gas_emissions_factor * model.gas_power[t]
#                 + model.co2_emissions[t] * model.flexible_power
#             )
#             / max_emission
#             for t in model.T
#         )

#         flexible_cost = flexible_power_cost * model.flexible_power

#         return (
#             w_cost * normalized_cost + w_emissions * normalized_emission + flexible_cost
#         )

#     model.objective = Objective(rule=objective_rule, sense=minimize)

#     # Constraints: Ensure heat demand is met at each time step
#     def heat_demand_rule(model, t):
#         return model.gas_power[t] + model.flexible_power >= model.heat_demand[t] * 0.99

#     model.heat_demand_constraint = Constraint(model.T, rule=heat_demand_rule)

#     # Solve the optimization problem
#     solver = SolverFactory("glpk")
#     results = solver.solve(model)

#     # Check solver status
#     if results.solver.termination_condition != TerminationCondition.optimal:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Optimization failed with termination condition {results.solver.termination_condition}",
#         )

#     # Extract the optimal flexible power value
#     try:
#         optimal_flexible_power = value(model.flexible_power)

#         return schemas.OptimizationResult(
#             optimal_flexible_power=optimal_flexible_power,
#             detail="Optimization completed successfully.",
#         )

#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error extracting results from optimization: {str(e)}",
#         )
