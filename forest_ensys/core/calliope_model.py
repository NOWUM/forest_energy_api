# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import calliope
import pandas as pd


def generate_calliope_model(
    model_dict: dict, electricity_data: pd.DataFrame, heat_data: pd.DataFrame
) -> calliope.Model:
    """
    Generates a calliope model from a dictionary.
    """
    model_def = calliope.AttrDict.from_yaml_string(str(model_dict))
    electricity_data.drop(columns=["id"], inplace=True)
    heat_data.drop(columns=["id"], inplace=True)
    electricity_data.rename(columns={"timestamp": "timesteps"}, inplace=True)
    heat_data.rename(columns={"timestamp": "timesteps"}, inplace=True)
    electricity_data = electricity_data.set_index("timesteps")
    heat_data = heat_data.set_index("timesteps")
    location_names = list(model_dict.get("nodes").keys())
    # rename columns
    electricity_data.columns = pd.MultiIndex.from_tuples(
        [(node, "demand_electricity") for node in location_names]
    )
    heat_data.columns = pd.MultiIndex.from_tuples(
        [(node, "demand_heat") for node in location_names]
    )
    electricity_data.columns.names = ["nodes", "techs"]
    heat_data.columns.names = ["nodes", "techs"]
    df = pd.concat([electricity_data, heat_data], axis=1)
    df.index = df.index.strftime("%Y-%m-%d %H:%M:%S")
    return calliope.Model(model_def, data_source_dfs={"demand_data": df})
