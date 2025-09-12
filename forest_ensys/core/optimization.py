# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from pyomo.environ import (
    ConcreteModel,
    Var,
    Objective,
    SolverFactory,
    NonNegativeReals,
    minimize,
    Constraint,
    RangeSet,
    Param,
    value,
    Binary,
)
import pandas as pd
import random


def optimize_dryers(
    co2_data: dict,
    heat_demand_data: dict,
    electricity_price_data: dict,
    electricity_demand: dict,
    window_type: dict,
    electric_heating: float,
    gas_emissions_factor: float,
    gas_price_data: dict,
    co2_price: float,
    ramp_up_rate: int = 1,
    ramp_down_rate: int = 1,
    minimum_runtime: int = 1,
    time_interval_hours: float = 1,
) -> dict:
    """
    Optimizes the use of flexible power for electric heating in a dryer system.
    Parameters:
    - co2_data: DataFrame containing the electricity footprint data.
    - heat_demand_data: DataFrame containing the heat demand data.
    - electricity_price_data: DataFrame containing the electricity price data.
    - electricity_demand: DataFrame containing the electricity demand data.
    - window_type: DataFrame containing the window type data.
    - electric_heating: Maximum flexible power available for electric heating (kW).
    - gas_emissions_factor: Emissions factor for gas heating (g/kWh).
    - gas_price_data: DataFrame containing the gas price data.
    - cost_per_mwh_gas: Cost of gas heating per MWh (€/MWh).
    - co2_price: Price of CO2 emissions (€/ton CO2).
    - ramp_up_rate: Maximum ramp-up rate for electric heating (kW/h).
    - ramp_down_rate: Maximum ramp-down rate for electric heating (kW/h).
    - minimum_runtime: Minimum runtime for electric heating (h).
    - time_interval_hours: Time interval for the optimization (h).
    Returns:
    - A dictionary containing the optimized results.
    """

    # check if heat_demand, co2_data and price_data have the same length
    if (
        len(heat_demand_data) != len(co2_data)
        or len(heat_demand_data) != len(electricity_price_data)
        or len(heat_demand_data) != len(electricity_demand)
    ):
        raise ValueError(
            "The length of heat_demand, co2_data and price_data must be the same."
        )

    # Initialize model
    model = ConcreteModel()

    num_periods = len(heat_demand_data)
    print(f"Number of periods: {num_periods}")
    print(f"Time interval: {time_interval_hours} hours")
    model.T = RangeSet(0, num_periods - 1, doc="Time periods (integer indices)")

    model.heat_demand = Param(model.T, initialize=heat_demand_data)
    model.co2_electricity = Param(model.T, initialize=co2_data)
    model.price_electricity = Param(model.T, initialize=electricity_price_data)
    model.price_gas = Param(model.T, initialize=gas_price_data)
    model.electricity_demand = Param(model.T, initialize=electricity_demand)
    model.window_type = Param(model.T, initialize=window_type)
    model.max_total_demand = Var(within=NonNegativeReals)

    model.flexible_power_max = electric_heating  # kW
    model.gas_emissions_factor = gas_emissions_factor  # g/kWh
    model.co2_price = co2_price  # €/ton CO2
    model.ramp_up_rate = ramp_up_rate
    model.ramp_down_rate = ramp_down_rate

    # Decision variables: Electric heating power used at each interval (kW)
    model.electric_power_used = Var(model.T, domain=NonNegativeReals)

    # Binary variable to track if the heater is running
    model.heater_on = Var(model.T, domain=Binary)

    # Auxiliary binary variable to track when the heater starts
    model.heater_start = Var(model.T, domain=Binary)

    # Constraints

    def ramp_up_rule(m, t):
        if t > 0:
            return (
                m.electric_power_used[t] - m.electric_power_used[t - 1]
                <= m.ramp_up_rate * time_interval_hours
            )
        return Constraint.Skip

    def ramp_down_rule(m, t):
        if t > 0:
            return (
                m.electric_power_used[t - 1] - m.electric_power_used[t]
                <= m.ramp_down_rate * time_interval_hours
            )
        return Constraint.Skip

    model.ramp_up = Constraint(model.T, rule=ramp_up_rule)
    model.ramp_down = Constraint(model.T, rule=ramp_down_rule)

    @model.Constraint(model.T)
    def heat_balance(m, t):
        return m.electric_power_used[t] * time_interval_hours <= m.heat_demand[t]

    @model.Constraint(model.T)
    def minimum_runtime_constraint(m, t):
        required_intervals = int(minimum_runtime / time_interval_hours)
        if t <= num_periods - required_intervals:
            # If heater turns on at t, it must stay on for required_intervals
            return sum(
                m.heater_on[t + i] for i in range(required_intervals)
            ) >= required_intervals * (
                m.heater_on[t] - (m.heater_on[t - 1] if t > 0 else 0)
            )
        else:
            # Near end of schedule: if heater turns on, it must stay on
            return sum(m.heater_on[t + i] for i in range(num_periods - t)) >= (
                num_periods - t
            ) * (m.heater_on[t] - (m.heater_on[t - 1] if t > 0 else 0))

    def max_electric_heating_rule(m, t):
        return m.electric_power_used[t] <= m.flexible_power_max * m.heater_on[t]

    model.max_electric_heating_constraint = Constraint(
        model.T, rule=max_electric_heating_rule
    )

    def electric_power_zero_when_off_rule(m, t):
        return m.electric_power_used[t] >= 0 * m.heater_on[t]

    model.electric_power_zero_when_off_constraint = Constraint(
        model.T, rule=electric_power_zero_when_off_rule
    )

    def electric_power_minimum_when_on_rule(m, t):
        return m.electric_power_used[t] >= 100 * m.heater_on[t]

    model.electric_power_minimum_when_on_constraint = Constraint(
        model.T, rule=electric_power_minimum_when_on_rule
    )

    def effective_total_demand(m, t):
        if m.window_type[t] != 1:
            return m.electricity_demand[t] + (
                m.electric_power_used[t] * time_interval_hours
            )
        else:
            return m.electricity_demand[t]

    def max_total_demand_rule(m, t):
        return m.max_total_demand >= effective_total_demand(m, t)

    model.max_total_demand_constraint = Constraint(model.T, rule=max_total_demand_rule)

    def full_load_hours_constraint_rule(m):
        total_demand = sum(effective_total_demand(m, t) for t in m.T)
        return total_demand >= (0.8*time_interval_hours*num_periods) * m.max_total_demand * (1 / time_interval_hours) # 0.8 is the minimum full load hours which is 7000 for one year

    model.full_load_hours_constraint = Constraint(rule=full_load_hours_constraint_rule)

    def total_cost_rule(m):
        electricity_cost = sum(
            m.electric_power_used[t]
            * m.price_electricity[t]
            * time_interval_hours
            * 1e-3
            for t in m.T
        )

        gas_cost = sum(
            (m.heat_demand[t] - (m.electric_power_used[t] * time_interval_hours))
            * m.price_gas[t]
            * 1e-3
            for t in m.T
        )

        emissions_gas = sum(
            (m.heat_demand[t] - (m.electric_power_used[t] * time_interval_hours))
            * m.gas_emissions_factor
            for t in m.T
        )
        emissions_electricity = sum(
            m.electric_power_used[t] * m.co2_electricity[t] * time_interval_hours
            for t in m.T
        )
        co2_cost = (emissions_gas + emissions_electricity) * 1e-6 * m.co2_price

        return electricity_cost + gas_cost + co2_cost

    model.total_cost = Objective(rule=total_cost_rule, sense=minimize)

    solver = SolverFactory("gurobi")
    solver.options["MIPGap"] = 0.001
    solver.options["TimeLimit"] = 120
    solver.options["OutputFlag"] = 1
    solver.options["Threads"] = 4
    
    results = solver.solve(model)

    print(results.solver.termination_condition)
    print(value(model.total_cost))

    optimized_results_df = pd.DataFrame(
        {
            "heat_demand_kwh": heat_demand_data.values(),
            "electric_power_used_kW": [
                value(model.electric_power_used[t]) for t in model.T
            ],
            "co2_electricity": co2_data.values(),
            "gas_price": gas_price_data.values(),
        }
    )
    optimized_results_df["gas_power_used_kwh"] = optimized_results_df[
        "heat_demand_kwh"
    ] - (optimized_results_df["electric_power_used_kW"] * time_interval_hours)

    optimized_results_df["emissions_gas"] = (
        optimized_results_df["gas_power_used_kwh"] * gas_emissions_factor
    )

    optimized_results_df["emissions_electricity"] = (
        optimized_results_df["electric_power_used_kW"]
        * optimized_results_df["co2_electricity"]
        * time_interval_hours
    )

    optimized_results_df["heater_on"] = [value(model.heater_on[t]) for t in model.T]

    total_energy_demand_kWh = optimized_results_df["heat_demand_kwh"].sum()
    electricity_used_kWh = (
        optimized_results_df["electric_power_used_kW"].sum() * time_interval_hours
    )
    gas_usage_kWh = total_energy_demand_kWh - electricity_used_kWh

    emissions_gas_only_tonnes = total_energy_demand_kWh * gas_emissions_factor * 1e-6

    cost_optimized_euro = value(model.total_cost)

    emissions_optimized_tonnes = (
        optimized_results_df["emissions_gas"].sum()
        + optimized_results_df["emissions_electricity"].sum()
    ) * 1e-6  # Gramm zu Tonnen

    emissions_savings_tonnes = emissions_gas_only_tonnes - emissions_optimized_tonnes

    # Cost savings calculation
    cost_gas_only = (
        (optimized_results_df["heat_demand_kwh"] / 1000)
        * optimized_results_df["gas_price"]
    ).sum() + (emissions_gas_only_tonnes * co2_price)
    cost_savings_euro = cost_gas_only - cost_optimized_euro

    return {
        "optimized_results_df": round(optimized_results_df, 2),
        "total_energy_demand": round(total_energy_demand_kWh, 2),
        "electricity_used": round(electricity_used_kWh, 2),
        "gas_usage": round(gas_usage_kWh, 2),
        "cost_savings": round(cost_savings_euro, 2),
        "cost_gas_only": round(cost_gas_only, 2),
        "cost_with_electric_heating": round(cost_optimized_euro, 2),
        "emissions_savings": round(emissions_savings_tonnes, 2),
        "emissions_gas_only": round(emissions_gas_only_tonnes, 2),
        "emissions_with_electric_heating": round(emissions_optimized_tonnes, 2),
    }


def test_optimize_dryers():
    """
    Test the optimize_dryers function with synthetic data to ensure constraints work as expected.
    """

    # Synthetic data
    time_intervals = 12  # 24 hours (1-hour intervals)
    time_interval_hours = 0.25  # Time interval in hours, e.g., 0.25 for 15 minutes,
    co2_data = {
        t: random.randint(0, 500)
        for t in range(int(time_intervals / time_interval_hours))
    }
    heat_demand_data = {
        t: random.randint(1000, 5000)
        for t in range(int(time_intervals / time_interval_hours))
    }
    price_data = {
        t: random.randint(0, 100)
        for t in range(int(time_intervals / time_interval_hours))
    }

    electric_heating = 200  # Max capacity of electric heating (kW)
    gas_emissions_factor = 250  # Gas emissions factor (g/kWh)
    cost_per_mwh_gas = 45  # Cost of gas heating (€/MWh)
    co2_price = 50  # Price of CO2 emissions (€/ton)
    ramp_up_rate = 100  # Max ramp-up rate (kW/h)
    ramp_down_rate = 100  # Max ramp-down rate (kW/h)
    minimum_runtime = 3  # Minimum runtime in hours

    # Run the optimization
    results = optimize_dryers(
        co2_data=co2_data,
        heat_demand_data=heat_demand_data,
        electricity_price_data=price_data,
        electric_heating=electric_heating,
        gas_emissions_factor=gas_emissions_factor,
        gas_price_data=cost_per_mwh_gas,
        co2_price=co2_price,
        ramp_up_rate=ramp_up_rate,
        ramp_down_rate=ramp_down_rate,
        minimum_runtime=minimum_runtime,
        time_interval_hours=time_interval_hours,
    )

    optimized_results_df = results["optimized_results_df"]

    print("Optimization completed successfully.")

    # Validation checks
    violations = []

    # Check if electric power used exceeds max capacity or heat demand
    for t, row in optimized_results_df.iterrows():
        if row["electric_power_used_kW"] > electric_heating:
            violations.append(f"Time {t}: Electric power used exceeds max capacity.")
        if row["electric_power_used_kW"] > row["heat_demand_kwh"]:
            violations.append(f"Time {t}: Electric power used exceeds heat demand.")

    # Check if ramp-up and ramp-down rates are respected
    for t in range(1, len(optimized_results_df)):
        ramp_up_diff = (
            optimized_results_df.loc[t, "electric_power_used_kW"]
            - optimized_results_df.loc[t - 1, "electric_power_used_kW"]
        )
        if ramp_up_diff > ramp_up_rate:
            violations.append(f"Time {t}: Ramp-up rate exceeded ({ramp_up_diff} kW).")

        ramp_down_diff = (
            optimized_results_df.loc[t - 1, "electric_power_used_kW"]
            - optimized_results_df.loc[t, "electric_power_used_kW"]
        )
        if ramp_down_diff > ramp_down_rate:
            violations.append(
                f"Time {t}: Ramp-down rate exceeded ({ramp_down_diff} kW)."
            )

    # Check if minimum consecutive runtime is respected
    heater_on_series = optimized_results_df["heater_on"]

    consecutive_runtime_violations = []

    current_run_length = 0
    for t, heater_on in enumerate(heater_on_series):
        if heater_on == 1:
            current_run_length += time_interval_hours
        else:
            if current_run_length > 0 and current_run_length < minimum_runtime:
                consecutive_runtime_violations.append(
                    f"Heater turned off after only {current_run_length} hours at time {t}."
                )
            current_run_length = 0

    if current_run_length > 0 and current_run_length < minimum_runtime:
        consecutive_runtime_violations.append(
            f"Heater turned off after only {current_run_length} hours at end of schedule."
        )

    violations.extend(consecutive_runtime_violations)

    # add a violation if heater on is 1 and electric power used is 0
    for t, row in optimized_results_df.iterrows():
        if row["heater_on"] == 1 and row["electric_power_used_kW"] == 0:
            violations.append(f"Time {t}: Heater is on but electric power used is 0.")
        if row["heater_on"] == 0 and row["electric_power_used_kW"] > 0:
            violations.append(
                f"Time {t}: Heater is off but electric power used is greater than 0."
            )

    #    print(optimized_results_df["heater_start"])
    print(optimized_results_df["heater_on"])
    print(optimized_results_df["electric_power_used_kW"])

    # Report results
    if violations:
        print("The following constraints were violated:")
        for violation in violations:
            print(f"- {violation}")
        print("\nTest failed due to constraint violations.")
    else:
        print("All constraints are satisfied. Test passed.")


# Run the test
# test_optimize_dryers()
