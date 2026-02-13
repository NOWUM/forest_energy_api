# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import requests
import pandas as pd
from io import StringIO
from typing import Optional
import logging

MAX_RETRY_ATTEMPTS = 2
logger = logging.getLogger(__name__)


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
    commodity_id: int,
    commodity_name: str,
    start_date_unix: int,
    second_start_date_unix: Optional[int] = None,
    retry_count: int = 0,
) -> pd.DataFrame:
    """
    Fetch data from SMARD API with retry logic.

    SMARD API quirk: Sometimes the exact timestamp doesn't work,
    so we try an alternate timestamp if the first fails.
    """
    if retry_count >= MAX_RETRY_ATTEMPTS:
        logger.error(f"Max retries reached for commodity {commodity_id}")
        return pd.DataFrame()

    url = f"https://www.smard.de/app/chart_data/{commodity_id}/DE/{commodity_id}_DE_quarterhour_{start_date_unix}.json"
    logger.info(f"Fetching data from: {url}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.warning(
            f"HTTP error for commodity {commodity_id} with timestamp {start_date_unix}: {e}"
        )
        # Try alternate timestamp if available
        if second_start_date_unix and retry_count == 0:
            logger.info(f"Retrying with alternate timestamp: {second_start_date_unix}")
            return get_data_per_commodity(
                commodity_id,
                commodity_name,
                second_start_date_unix,
                None,
                retry_count + 1,
            )
        return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for commodity {commodity_id}: {e}")
        return pd.DataFrame()

    try:
        data = response.json()
        timeseries = pd.DataFrame(data.get("series", []))

        if timeseries.empty:
            logger.warning(f"Empty data received for commodity {commodity_id}")
            return pd.DataFrame()

        # Convert unix timestamp to datetime
        timeseries[0] = pd.to_datetime(timeseries[0], unit="ms", utc=True)
        timeseries.columns = ["timestamp", "mwh"]
        timeseries["commodity_id"] = commodity_id
        timeseries["commodity_name"] = commodity_name
        timeseries = timeseries.dropna(subset=["mwh"])

        return timeseries

    except (ValueError, KeyError) as e:
        logger.error(f"Failed to parse response for commodity {commodity_id}: {e}")
        return pd.DataFrame()
