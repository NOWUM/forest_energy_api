# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import pandas as pd
from datetime import timedelta
import numpy as np


def ensure_consistent_granularity(df, method="mean") -> tuple[pd.DataFrame, float]:
    """
    Ensures that the DataFrame has a consistent granularity.

    Parameters:
    ----------
    df : pd.DataFrame
        The DataFrame to check and resample.
    method : str, optional
        The method to use for resampling (default is "mean").

    Returns:
    -------
    a float representing the granularity of the dataframe
    """

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    granularity = df["timestamp"].diff().min()
    df_resampled = (
        df.set_index("timestamp").resample(granularity).agg(method).reset_index()
    )
    return df_resampled, granularity.total_seconds() / 3600


def check_granularity_and_merge(df1, df2, method="mean"):
    """
    Checks the granularity of the two DataFrames and merges them.

    Parameters:
    ----------
    df1 : pd.DataFrame
        The first DataFrame.
    df2 : pd.DataFrame
        The second DataFrame.

    Returns:
    -------
    pd.DataFrame
        The merged DataFrame.
    """
    df1["timestamp"] = pd.to_datetime(df1["timestamp"], utc=True)
    df2["timestamp"] = pd.to_datetime(df2["timestamp"], utc=True)
    df1_granularity = df1["timestamp"].diff().min()
    df2_granularity = df2["timestamp"].diff().min()
    if df1_granularity < df2_granularity:
        df1_resampled = (
            df1.set_index("timestamp")
            .resample(df2_granularity)
            .agg(method)
            .reset_index()
        )
        df2_resampled = df2
    else:
        df2_resampled = (
            df2.set_index("timestamp")
            .resample(df1_granularity)
            .agg(method)
            .reset_index()
        )
        df1_resampled = df1
    return pd.merge(df1_resampled, df2_resampled, on="timestamp", how="inner")


def get_reference_day(date):
    weekday = date.weekday()
    if weekday < 5:  # Mon-Fri
        days_back = 1 if weekday > 0 else 3
        ref_date = date - timedelta(days=days_back)
    else:
        ref_date = date - timedelta(days=7)
    return ref_date.date()


def select_peaks_no_overlap(
    day_df, window_size, price_col, time_window_start, time_window_end, kind="min"
):
    """
    Select up to two non-overlapping peak timestamps (min or max) between time_window_start and time_window_end.
    Each window is [peak_time - 2h, peak_time + 2h), i.e. 16 quarters.
    Windows must not overlap.
    Returns a list of peak timestamps.
    """
    if time_window_start is not None and time_window_end is not None:
        effective_start = time_window_start
        effective_end   = time_window_end
    else:
        # 24h mode: constrain peaks so windows always stay within one calendar day
        effective_start = int(window_size / 2)          # e.g. 3 for window_size=6
        effective_end   = int(24 - window_size / 2) # e.g. 20 for window_size=6

    mask = (
        (day_df["timestamp"].dt.hour >= effective_start)
        & (day_df["timestamp"].dt.hour <= effective_end)
    )
    df = day_df[mask].copy()
    if df.empty:
        return []
    # Sort by price
    if kind == "min":
        sorted_df = df.sort_values(price_col, ascending=True)
    else:
        sorted_df = df.sort_values(price_col, ascending=False)
    peaks = []
    for _, row in sorted_df.iterrows():
        peak_time = row["timestamp"]
        too_close = any(
            abs((peak_time - p).total_seconds()) < window_size * 3600
            for p in peaks
        )
        if not too_close:
            peaks.append(peak_time)
        if len(peaks) == 2:
            break
    return sorted(peaks)


def calculate_dynamic_network_fee(
    merged_data,
    network_fee_value,
    relative_network_fee_reduction,
    relative_network_fee_surcharge,
    window_size,
    time_window_start,
    time_window_end,
    use_reference_day: bool = True,
):
    merged_data = merged_data.copy()
    merged_data["timestamp"] = pd.to_datetime(merged_data["timestamp"])
    merged_data = merged_data.sort_values("timestamp").reset_index(drop=True)
    merged_data["date"] = merged_data["timestamp"].dt.date

    # Step 1: For each day, find non-overlapping min/max peaks
    peak_info = {}
    for date, group in merged_data.groupby("date"):
        min_peaks = select_peaks_no_overlap(
            group,
            window_size,
            price_col="electricity_price",
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            kind="min",
        )
        max_peaks = select_peaks_no_overlap(
            group,
            window_size,
            price_col="electricity_price",
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            kind="max",
        )
        peak_info[date] = {"min_peaks": min_peaks, "max_peaks": max_peaks}

    # Step 2: For each day, apply the reference day's windows
    merged_data["in_low_window"] = False
    merged_data["in_high_window"] = False

    tz = merged_data["timestamp"].dt.tz

    for date in merged_data["date"].unique():
        if use_reference_day:
            ref_date = get_reference_day(pd.Timestamp(date))
        else:
            ref_date = date

        if ref_date not in peak_info:
            continue

        # Anchor the target day for window reconstruction
        target_start = pd.Timestamp(date)
        if tz is not None:
            target_start = target_start.tz_localize(tz)
        target_end = target_start + timedelta(days=1)  # exclusive

        for window_col, peaks in (
            ("in_low_window",  peak_info[ref_date]["min_peaks"]),
            ("in_high_window", peak_info[ref_date]["max_peaks"]),
        ):
            for peak_time in peaks:
                # Compute peak's own day start (matching target timezone)
                peak_day_start = pd.Timestamp(peak_time.date())
                if tz is not None:
                    peak_day_start = peak_day_start.tz_localize(tz)

                # Offsets from peak's day start — preserves cross-midnight correctly
                start_offset = (peak_time - timedelta(hours=window_size / 2)) - peak_day_start
                end_offset   = (peak_time + timedelta(hours=window_size / 2)) - peak_day_start

                # Apply same offsets to the target date
                ts_start = target_start + start_offset
                ts_end   = target_start + end_offset

                # Cap to target day
                ts_start = max(ts_start, target_start)
                ts_end   = min(ts_end,   target_end)

                if ts_start >= ts_end:
                    continue

                mask = (
                    (merged_data["timestamp"] >= ts_start)
                    & (merged_data["timestamp"] < ts_end)
                )
                merged_data.loc[mask, window_col] = True

    # Step 3: High price window takes precedence
    # merged_data['window_type'] = np.where(
    #     merged_data['in_high_window'], 'high',
    #     np.where(merged_data['in_low_window'], 'low', 'normal')
    # )
    # Step 3: Low price window takes precedence
    merged_data["window_type"] = np.where(
        merged_data["in_low_window"],
        1,
        np.where(merged_data["in_high_window"], 2, 0),
    )

    # Step 4: Calculate dynamic price
    merged_data["electricity_price"] = merged_data.apply(
        lambda row: (
            row["electricity_price"]
            + (
                network_fee_value * (1 - relative_network_fee_reduction)
                if row["window_type"] == 1
                else network_fee_value * (1 + relative_network_fee_surcharge)
                if row["window_type"] == 2
                else network_fee_value
            )
        ),
        axis=1,
    )

    return merged_data


# df = pd.DataFrame({
#     'timestamp': pd.date_range("2025-03-01 00:00", periods=4800, freq="15min"),
#     'electricity_price': np.random.uniform(50, 200, 4800)
# })

# result = calculate_dynamic_network_fee(
#     df,
#     network_fee_value=20,
#     relative_network_fee_reduction=0.8,  # 80% Reduktion im Niedrigpreisfenster
#     relative_network_fee_surcharge=0.5   # 50% Zuschlag im Hochpreisfenster
# )

# print(result[['timestamp', 'electricity_price', 'dynamic_price', 'window_type']])
# result.to_csv('dynamic_prices.csv', index=False)
