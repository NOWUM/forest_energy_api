# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import requests
import pandas as pd
import json
from io import StringIO


def crawl_emissions_data() -> pd.DataFrame:
    """
    Crawl the emissions data from the Electricity Maps database.
    """
    spreadsheet_id = "1ukTAD_oQKZfq-FgLpbLo_bGOv-UPTaoM_WS316xlDcE"
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv"
    response = requests.get(url)
    try:
        response.raise_for_status()
    except Exception as e:
        print(f"Coult not crawl emissions data: {e}")
    df = pd.read_csv(StringIO(response.text))
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.dropna()
    return df


def get_data_per_commodity(
    commodity_id, commodity_name, start_date_unix, second_start_date_unix=None
) -> pd.DataFrame:
    url = f"https://www.smard.de/app/chart_data/{commodity_id}/DE/{commodity_id}_DE_quarterhour_{start_date_unix}.json"
    print(url)
    response = requests.get(url)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(
            f"Could not get data for commodity: {commodity_id} {e} trying different start date"
        )
        return get_data_per_commodity(
            commodity_id, commodity_name, second_start_date_unix
        )
    data = json.loads(response.text)
    timeseries = pd.DataFrame.from_dict(data["series"])
    if timeseries.empty:
        print(f"Received empty data for commodity: {commodity_id}")
    timeseries[0] = pd.to_datetime(timeseries[0], unit="ms", utc=True)
    timeseries.columns = ["timestamp", "mwh"]
    timeseries["commodity_id"] = commodity_id
    timeseries["commodity_name"] = commodity_name
    timeseries = timeseries.dropna(subset="mwh")

    return timeseries
