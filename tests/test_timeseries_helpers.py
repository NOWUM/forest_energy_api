# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
tests/test_timeseries_helpers.py

Tests for select_peaks_no_overlap and calculate_dynamic_network_fee.

Run with:
    pytest tests/test_timeseries_helpers.py -v
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta

import importlib.util
import pathlib

_mod_path = (
    pathlib.Path(__file__).parent.parent
    / "forest_ensys"
    / "core"
    / "timeseries_helpers.py"
)
_spec = importlib.util.spec_from_file_location("timeseries_helpers", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

select_peaks_no_overlap = _mod.select_peaks_no_overlap
calculate_dynamic_network_fee = _mod.calculate_dynamic_network_fee

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
WINDOW_SIZE = 6  # hours — BK4-22-089 compliant default for tests


def make_day(
    base_date: str = "2024-01-02",
    base_price: float = 50.0,
    price_overrides: dict = None,
    tz: str = None,
) -> pd.DataFrame:
    """
    Build a single-day DataFrame of 15-min intervals.

    Parameters
    ----------
    base_date : str
        ISO date string for the day, e.g. "2024-01-02".
    base_price : float
        Default electricity price for all intervals.
    price_overrides : dict
        {hour_int: price} to inject specific prices at exact hours.
        Minutes default to :00 of that hour.
    tz : str, optional
        Timezone string, e.g. "UTC". None means timezone-naive.

    Returns
    -------
    pd.DataFrame with columns [timestamp, electricity_price]
    """
    timestamps = pd.date_range(
        start=f"{base_date} 00:00", periods=96, freq="15min", tz=tz
    )
    prices = [base_price] * 96
    df = pd.DataFrame({"timestamp": timestamps, "electricity_price": prices})

    if price_overrides:
        for hour, price in price_overrides.items():
            mask = df["timestamp"].dt.hour == hour
            df.loc[mask, "electricity_price"] = price

    return df


def make_multi_day(
    start_date: str,
    n_days: int,
    base_price: float = 50.0,
    daily_overrides: dict = None,
    tz: str = "UTC",
) -> pd.DataFrame:
    """
    Build a multi-day merged_data DataFrame suitable for
    calculate_dynamic_network_fee.

    Parameters
    ----------
    start_date : str
        ISO date string for the first day.
    n_days : int
        Number of days to generate.
    base_price : float
        Default electricity price.
    daily_overrides : dict
        {date_str: {hour: price}} for controlled price injection.
    tz : str
        Timezone. Defaults to "UTC" to match production data flow.

    Returns
    -------
    pd.DataFrame with columns [timestamp, electricity_price]
    """
    start = pd.Timestamp(start_date, tz=tz)
    end = start + timedelta(days=n_days) - timedelta(minutes=15)
    timestamps = pd.date_range(start=start, end=end, freq="15min")
    prices = [base_price] * len(timestamps)
    df = pd.DataFrame({"timestamp": timestamps, "electricity_price": prices})

    if daily_overrides:
        for date_str, hour_map in daily_overrides.items():
            for hour, price in hour_map.items():
                mask = (df["timestamp"].dt.date == pd.Timestamp(date_str).date()) & (
                    df["timestamp"].dt.hour == hour
                )
                df.loc[mask, "electricity_price"] = price

    return df


def get_peak_hours(peaks: list) -> list[int]:
    """Return sorted list of hours from a list of Timestamps."""
    return sorted(p.hour for p in peaks)


# ---------------------------------------------------------------------------
# Tests: select_peaks_no_overlap
# ---------------------------------------------------------------------------


class TestSelectPeaksNoOverlap:
    # --- Basic selection ---

    def test_returns_at_most_two_peaks(self):
        """Never returns more than 2 peaks regardless of input size."""
        day = make_day(price_overrides={8: 10, 10: 12, 16: 8, 20: 9})
        peaks = select_peaks_no_overlap(
            day,
            WINDOW_SIZE,
            "electricity_price",
            time_window_start=6,
            time_window_end=21,
            kind="min",
        )
        assert len(peaks) <= 2

    def test_selects_lowest_prices_for_min(self):
        """The two cheapest non-overlapping hours are selected for kind=min."""
        day = make_day(
            price_overrides={
                8: 5,  # cheapest → selected first
                11: 6,  # second cheapest, only 3h from 8h → strictly overlaps → skipped
                20: 7,  # third cheapest, 12h from 8h → no overlap → selected second
            }
        )
        peaks = select_peaks_no_overlap(
            day,
            WINDOW_SIZE,
            "electricity_price",
            time_window_start=6,
            time_window_end=21,
            kind="min",
        )
        hours = get_peak_hours(peaks)
        assert 8 in hours
        assert 11 not in hours, "11h is only 3h from 8h — must be skipped"
        assert 20 in hours

    def test_selects_highest_prices_for_max(self):
        """The two most expensive non-overlapping hours are selected for kind=max."""
        day = make_day(
            price_overrides={
                9: 200,  # most expensive
                21: 180,  # second most expensive, far away
                12: 190,  # third — too close to 9h
            }
        )
        peaks = select_peaks_no_overlap(
            day,
            WINDOW_SIZE,
            "electricity_price",
            time_window_start=6,
            time_window_end=21,
            kind="max",
        )
        hours = get_peak_hours(peaks)
        assert 9 in hours
        assert 21 in hours

    # --- Non-overlap enforcement ---

    def test_overlapping_candidates_skipped(self):
        """
        If the two cheapest prices are within window_size hours,
        the second must be skipped and the next valid one used instead.
        """
        # 8h cheapest, 10h second cheapest (2h apart, < 6h → overlap),
        # 20h third cheapest (far away → valid second peak)
        day = make_day(price_overrides={8: 5, 10: 6, 20: 7})
        peaks = select_peaks_no_overlap(
            day,
            WINDOW_SIZE,
            "electricity_price",
            time_window_start=6,
            time_window_end=21,
            kind="min",
        )
        hours = get_peak_hours(peaks)
        assert 8 in hours
        assert 10 not in hours, "10h overlaps with 8h window, must be skipped"
        assert 20 in hours

    def test_two_selected_peaks_are_window_size_hours_apart(self):
        """
        For any random-price day, the two selected peaks must always be
        at least window_size hours apart (non-overlap guarantee).
        """
        rng = np.random.default_rng(seed=42)
        for _ in range(50):
            prices = rng.uniform(0, 100, 96)
            timestamps = pd.date_range("2024-06-01 00:00", periods=96, freq="15min")
            day = pd.DataFrame({"timestamp": timestamps, "electricity_price": prices})
            for kind in ("min", "max"):
                peaks = select_peaks_no_overlap(
                    day,
                    WINDOW_SIZE,
                    "electricity_price",
                    time_window_start=6,
                    time_window_end=21,
                    kind=kind,
                )
                if len(peaks) == 2:
                    distance_hours = abs((peaks[1] - peaks[0]).total_seconds()) / 3600
                    assert distance_hours >= WINDOW_SIZE, (
                        f"Peaks at {peaks[0].hour}h and {peaks[1].hour}h are only "
                        f"{distance_hours:.1f}h apart (< {WINDOW_SIZE}h)"
                    )

    # --- Adjacent windows (BK4-22-089 explicitly allowed) ---

    def test_adjacent_windows_accepted(self):
        """
        Two peaks exactly window_size hours apart must BOTH be accepted.
        BK4-22-089 FAQ: peak at 20:00 following a 14:00 peak with 6h windows
        is a valid minimal separation and must not be rejected.
        """
        # 8h cheapest, 14h second cheapest — exactly WINDOW_SIZE=6h apart
        day = make_day(price_overrides={8: 5, 14: 6})
        peaks = select_peaks_no_overlap(
            day,
            WINDOW_SIZE,
            "electricity_price",
            time_window_start=6,
            time_window_end=21,
            kind="min",
        )
        hours = get_peak_hours(peaks)
        assert 8 in hours, "First peak at 8h must be selected"
        assert 14 in hours, (
            "Second peak at 14h is exactly window_size hours away — must be accepted "
            "(BK4-22-089 adjacent window rule)"
        )

    # --- Time window constraints ---

    def test_time_constraint_excludes_out_of_range_peaks(self):
        """Peaks outside [time_window_start, time_window_end] are ignored."""
        # Cheapest price is at 03:00 (outside 06-21 window)
        day = make_day(price_overrides={3: 1, 10: 10, 18: 11})
        peaks = select_peaks_no_overlap(
            day,
            WINDOW_SIZE,
            "electricity_price",
            time_window_start=6,
            time_window_end=21,
            kind="min",
        )
        hours = get_peak_hours(peaks)
        assert 3 not in hours, "Hour 3 is outside the allowed window"
        assert 10 in hours

    def test_empty_day_returns_empty(self):
        """Empty DataFrame returns empty list."""
        day = pd.DataFrame(
            {
                "timestamp": pd.Series(dtype="datetime64[ns]"),
                "electricity_price": pd.Series(dtype=float),
            }
        )
        peaks = select_peaks_no_overlap(
            day,
            WINDOW_SIZE,
            "electricity_price",
            time_window_start=6,
            time_window_end=21,
            kind="min",
        )
        assert peaks == []

    def test_no_timestamps_in_time_window_returns_empty(self):
        """If no timestamps fall inside the time window, return empty list."""
        # All data between 22:00-23:45, window is 06:00-21:00
        timestamps = pd.date_range("2024-01-02 22:00", periods=8, freq="15min")
        day = pd.DataFrame({"timestamp": timestamps, "electricity_price": [50.0] * 8})
        peaks = select_peaks_no_overlap(
            day,
            WINDOW_SIZE,
            "electricity_price",
            time_window_start=6,
            time_window_end=21,
            kind="min",
        )
        assert peaks == []

    def test_only_one_valid_peak(self):
        """If only one non-overlapping peak can be found, return list of length 1."""
        # Only one price dip, and no other timestamps far enough away
        timestamps = pd.date_range("2024-01-02 10:00", periods=16, freq="15min")
        prices = [50.0] * 16
        prices[0] = 5.0  # single minimum
        day = pd.DataFrame({"timestamp": timestamps, "electricity_price": prices})
        peaks = select_peaks_no_overlap(
            day,
            WINDOW_SIZE,
            "electricity_price",
            time_window_start=None,
            time_window_end=None,
            kind="min",
        )
        assert len(peaks) == 1

    def test_peaks_are_returned_sorted(self):
        """Returned list is always sorted ascending by timestamp."""
        day = make_day(price_overrides={18: 5, 8: 7})
        peaks = select_peaks_no_overlap(
            day,
            WINDOW_SIZE,
            "electricity_price",
            time_window_start=6,
            time_window_end=21,
            kind="min",
        )
        assert peaks == sorted(peaks)


# ---------------------------------------------------------------------------
# Tests: calculate_dynamic_network_fee
# ---------------------------------------------------------------------------


class TestCalculateDynamicNetworkFee:
    # Shared fee parameters
    FEE = 20.0
    REDUCTION = 0.8  # low window fee = 20 * 0.2 = 4
    SURCHARGE = 0.1  # high window fee = 20 * 1.1 = 22

    def _base_params(self):
        return dict(
            network_fee_value=self.FEE,
            relative_network_fee_reduction=self.REDUCTION,
            relative_network_fee_surcharge=self.SURCHARGE,
            window_size=WINDOW_SIZE,
            time_window_start=6,
            time_window_end=21,
        )

    # --- window_type values ---

    def test_window_type_only_valid_values(self):
        """window_type must only contain 0, 1, or 2 — never anything else."""
        data = make_multi_day("2024-01-01", n_days=7)
        result = calculate_dynamic_network_fee(
            data, use_reference_day=False, **self._base_params()
        )
        assert set(result["window_type"].unique()).issubset({0, 1, 2})

    def test_all_rows_have_window_type(self):
        """No NaN values in window_type after calculation."""
        data = make_multi_day("2024-01-01", n_days=3)
        result = calculate_dynamic_network_fee(
            data, use_reference_day=False, **self._base_params()
        )
        assert result["window_type"].notna().all()

    # --- Low window takes precedence ---

    def test_low_window_takes_precedence_over_high(self):
        """
        When a timestamp falls in both a low and high window,
        window_type must be 1 (low), not 2 (high).
        Cross-type overlap is allowed by BK4-22-089 and low wins.
        """
        # Inject min and max peaks at the same hour to force overlap
        data = make_multi_day(
            "2024-01-01",
            n_days=2,
            daily_overrides={
                "2024-01-01": {10: 1, 20: 200},  # min=10h, max=20h — will inform day 2
            },
        )
        result = calculate_dynamic_network_fee(
            data, use_reference_day=True, **self._base_params()
        )
        # Any timestamp tagged as both (in_low_window AND in_high_window)
        # must resolve to window_type=1, not 2
        if "in_low_window" in result.columns and "in_high_window" in result.columns:
            overlap = result[result["in_low_window"] & result["in_high_window"]]
            assert (overlap["window_type"] == 1).all(), (
                "Timestamps in both low and high window must have window_type=1"
            )

    # --- Fee formula correctness ---

    def test_fee_formula_low_window(self):
        """
        In low windows: effective_price = market_price + fee * (1 - reduction)
        With fee=20, reduction=0.8: surcharge = 4.0 €/MWh
        """
        market_price = 50.0
        expected_low = market_price + self.FEE * (1 - self.REDUCTION)  # 54.0

        data = make_multi_day(
            "2024-01-01",
            n_days=2,
            daily_overrides={"2024-01-01": {10: 1}},  # clear min peak at 10h
        )
        result = calculate_dynamic_network_fee(
            data, use_reference_day=True, **self._base_params()
        )
        low_rows = result[result["window_type"] == 1]
        if not low_rows.empty:
            # Check at least one row with expected base price
            base_price_rows = low_rows[
                np.isclose(low_rows["electricity_price"], expected_low, atol=0.01)
            ]
            assert not base_price_rows.empty, (
                f"Expected at least one low-window row with price ≈ {expected_low}, "
                f"got: {low_rows['electricity_price'].unique()}"
            )

    def test_fee_formula_high_window(self):
        """
        In high windows: effective_price = market_price + fee * (1 + surcharge)
        With fee=20, surcharge=0.1: surcharge = 22.0 €/MWh
        """
        market_price = 50.0
        expected_high = market_price + self.FEE * (1 + self.SURCHARGE)  # 72.0

        data = make_multi_day(
            "2024-01-01",
            n_days=2,
            daily_overrides={"2024-01-01": {10: 200}},  # clear max peak at 10h
        )
        result = calculate_dynamic_network_fee(
            data, use_reference_day=True, **self._base_params()
        )
        high_rows = result[result["window_type"] == 2]
        if not high_rows.empty:
            base_price_rows = high_rows[
                np.isclose(high_rows["electricity_price"], expected_high, atol=0.01)
            ]
            assert not base_price_rows.empty, (
                f"Expected high-window rows with price ≈ {expected_high}, "
                f"got: {high_rows['electricity_price'].unique()}"
            )

    def test_fee_formula_neutral_window(self):
        """
        In neutral windows (window_type=0):
        effective_price = market_price + fee (full, no reduction or surcharge)
        """
        market_price = 50.0
        expected_neutral = market_price + self.FEE  # 70.0

        data = make_multi_day("2024-01-01", n_days=1)
        result = calculate_dynamic_network_fee(
            data, use_reference_day=False, **self._base_params()
        )
        neutral_rows = result[result["window_type"] == 0]
        if not neutral_rows.empty:
            prices = neutral_rows["electricity_price"].round(4)
            assert (prices == round(expected_neutral, 4)).all(), (
                f"Neutral rows should all have price = {expected_neutral}"
            )

    # --- use_reference_day logic ---

    def test_predictive_uses_same_day_peaks(self):
        """
        use_reference_day=False: windows are defined by the same day's prices.
        A day with a clear price minimum should tag its own low-price window.
        """
        data = make_multi_day(
            "2024-01-01",
            n_days=1,
            daily_overrides={"2024-01-01": {10: 1}},  # clear minimum at 10h
        )
        result = calculate_dynamic_network_fee(
            data, use_reference_day=False, **self._base_params()
        )
        low_rows = result[result["window_type"] == 1]
        assert not low_rows.empty, (
            "Predictive mode must tag low-price windows based on same day's prices"
        )

    def test_bk4_first_day_has_no_windows(self):
        """
        use_reference_day=True (BK4-22-089): the very first day in the dataset
        has no reference day in peak_info → all window_type must be 0.
        This is an inherent property of the backward-looking approach.
        """
        # Tuesday 2024-01-02 → reference = Monday 2024-01-01 → not in dataset
        data = make_multi_day(
            "2024-01-02",
            n_days=1,
            daily_overrides={"2024-01-02": {10: 1, 18: 200}},
        )
        result = calculate_dynamic_network_fee(
            data, use_reference_day=True, **self._base_params()
        )
        assert (result["window_type"] == 0).all(), (
            "First day with no reference in dataset must have all window_type=0"
        )

    def test_bk4_second_day_uses_first_day_peaks(self):
        """
        use_reference_day=True: Day 2 (Tuesday) uses Day 1 (Monday) peaks.
        A clear minimum on Day 1 must produce low-price windows on Day 2.
        """
        # Monday + Tuesday: inject cheap hour only on Monday
        data = make_multi_day(
            "2024-01-01",
            n_days=2,
            daily_overrides={"2024-01-01": {10: 1}},  # Monday has cheap hour at 10h
        )
        result = calculate_dynamic_network_fee(
            data, use_reference_day=True, **self._base_params()
        )
        tuesday = result[result["timestamp"].dt.date == date(2024, 1, 2)]
        assert (tuesday["window_type"] == 1).any(), (
            "Tuesday must have low-price windows based on Monday's cheap hour"
        )

    def test_predictive_vs_bk4_differ_on_volatile_prices(self):
        """
        When prices differ significantly day-to-day, predictive and BK4-22-089
        must produce different window assignments — this is the core paper hypothesis.
        """
        # Day 1 (Mon): cheap at 8h — BK4 will apply this to Day 2
        # Day 2 (Tue): cheap at 20h — predictive will apply this to Day 2
        data = make_multi_day(
            "2024-01-01",
            n_days=2,
            daily_overrides={
                "2024-01-01": {8: 1},
                "2024-01-02": {20: 1},
            },
        )
        params = self._base_params()

        result_bk4 = calculate_dynamic_network_fee(
            data.copy(), use_reference_day=True, **params
        )
        result_pred = calculate_dynamic_network_fee(
            data.copy(), use_reference_day=False, **params
        )

        tuesday_bk4 = result_bk4[result_bk4["timestamp"].dt.date == date(2024, 1, 2)]
        tuesday_pred = result_pred[result_pred["timestamp"].dt.date == date(2024, 1, 2)]

        low_hours_bk4 = set(
            tuesday_bk4[tuesday_bk4["window_type"] == 1]["timestamp"].dt.hour
        )
        low_hours_pred = set(
            tuesday_pred[tuesday_pred["window_type"] == 1]["timestamp"].dt.hour
        )

        # BK4 should see low windows around hour 8 (from Monday)
        assert 8 in low_hours_bk4, (
            "BK4: Tuesday low window should mirror Monday's cheap hour (8h)"
        )
        # Predictive should see low windows around hour 20 (today's own minimum)
        assert 20 in low_hours_pred, (
            "Predictive: Tuesday low window should use today's cheap hour (20h)"
        )
        # They must differ
        assert low_hours_bk4 != low_hours_pred, (
            "BK4 and predictive must assign different low windows when price patterns change day-to-day"
        )

    # --- Midnight-crossing windows (24h mode) ---

    def test_midnight_crossing_window_tagged_correctly(self):
        """
        When time_window_start=None and time_window_end=None (24h mode),
        a peak near midnight produces a window that crosses into the next day.
        Timestamps on both sides of midnight must be tagged.
        """
        # Peak at 23:00 with window_size=2 → window = [21:45, 01:00 next day]
        data = make_multi_day(
            "2024-01-01",
            n_days=2,
            daily_overrides={"2024-01-01": {23: 1}},  # minimum at 23h
        )
        params = {
            **self._base_params(),
            "time_window_start": None,
            "time_window_end": None,
            "window_size": 2,
        }
        result = calculate_dynamic_network_fee(data, use_reference_day=False, **params)

        # With predictive mode: Day 1 low window around 23h → should include 23h itself
        day1_late = result[
            (result["timestamp"].dt.date == date(2024, 1, 1))
            & (result["timestamp"].dt.hour == 23)
        ]
        assert (day1_late["window_type"] == 1).any(), (
            "Timestamps at 23:00 should be in the low-price window"
        )

    # --- Data integrity ---

    def test_input_dataframe_not_mutated(self):
        """calculate_dynamic_network_fee must not modify the input DataFrame in place."""
        data = make_multi_day("2024-01-01", n_days=3)
        original_prices = data["electricity_price"].copy()

        calculate_dynamic_network_fee(
            data, use_reference_day=False, **self._base_params()
        )

        pd.testing.assert_series_equal(
            data["electricity_price"],
            original_prices,
            check_names=False,
        )

    def test_output_row_count_matches_input(self):
        """Output must have exactly the same number of rows as input."""
        data = make_multi_day("2024-01-01", n_days=5)
        result = calculate_dynamic_network_fee(
            data, use_reference_day=False, **self._base_params()
        )
        assert len(result) == len(data)

    def test_random_prices_never_crash(self):
        """
        For 100 random-price datasets, the function must complete without
        exceptions and return valid window_type values.
        """
        rng = np.random.default_rng(seed=99)
        for i in range(100):
            prices = rng.uniform(-10, 200, 96 * 3)  # 3 days, includes negatives
            timestamps = pd.date_range(
                "2024-01-01", periods=len(prices), freq="15min", tz="UTC"
            )
            data = pd.DataFrame({"timestamp": timestamps, "electricity_price": prices})
            result = calculate_dynamic_network_fee(
                data, use_reference_day=bool(i % 2), **self._base_params()
            )
            assert set(result["window_type"].unique()).issubset({0, 1, 2}), (
                f"Iteration {i}: unexpected window_type values"
            )


# ---------------------------------------------------------------------------
# Additional Tests: Multi-day coverage
# ---------------------------------------------------------------------------


class TestSelectPeaksMultipleDays:
    def test_consistent_across_full_week(self):
        """
        select_peaks_no_overlap must behave consistently across all 7 weekdays.
        For each day: the cheapest non-overlapping hours must be selected
        regardless of which weekday it is (the function is stateless per day).
        """
        for day_offset in range(7):
            base = f"2024-01-{day_offset + 1:02d}"  # 2024-01-01 is Monday
            day = make_day(
                base_date=base,
                price_overrides={8: 5, 20: 7},  # two clear non-overlapping minima
            )
            peaks = select_peaks_no_overlap(
                day,
                WINDOW_SIZE,
                "electricity_price",
                time_window_start=6,
                time_window_end=21,
                kind="min",
            )
            hours = get_peak_hours(peaks)
            assert 8 in hours, f"Day offset {day_offset}: peak at 8h must be selected"
            assert 20 in hours, f"Day offset {day_offset}: peak at 20h must be selected"

    def test_each_day_independently_graded(self):
        """
        Verify that fuzz-testing across 30 days individually all satisfy
        the non-overlap guarantee — confirming the function is truly stateless.
        """
        rng = np.random.default_rng(seed=7)
        for d in range(30):
            base = pd.Timestamp("2024-01-01") + timedelta(days=d)
            timestamps = pd.date_range(base, periods=96, freq="15min")
            prices = rng.uniform(0, 100, 96)
            day = pd.DataFrame({"timestamp": timestamps, "electricity_price": prices})

            for kind in ("min", "max"):
                peaks = select_peaks_no_overlap(
                    day,
                    WINDOW_SIZE,
                    "electricity_price",
                    time_window_start=6,
                    time_window_end=21,
                    kind=kind,
                )
                if len(peaks) == 2:
                    dist = abs((peaks[1] - peaks[0]).total_seconds()) / 3600
                    assert dist >= WINDOW_SIZE, (
                        f"Day {d} ({kind}): peaks {peaks[0].hour}h and "
                        f"{peaks[1].hour}h are {dist:.2f}h apart — violates non-overlap"
                    )


class TestCalculateDynamicNetworkFeeMultipleDays:
    FEE, REDUCTION, SURCHARGE = 20.0, 0.8, 0.1

    def _base_params(self, start=6, end=21):
        return dict(
            network_fee_value=self.FEE,
            relative_network_fee_reduction=self.REDUCTION,
            relative_network_fee_surcharge=self.SURCHARGE,
            window_size=WINDOW_SIZE,
            time_window_start=start,
            time_window_end=end,
        )

    # --- BK4-22-089 reference day mapping across a full week ---

    def test_bk4_weekday_reference_mapping(self):
        """
        BK4-22-089 reference day rules:
          Monday    (weekday=0) → previous Friday  (-3 days)
          Tue–Fri   (weekday=1-4) → previous day   (-1 day)
          Saturday  (weekday=5) → previous Saturday (-7 days)
          Sunday    (weekday=6) → previous Sunday   (-7 days)

        Build 3 weeks of data; inject cheap hours only on specific reference days
        and verify the correct target days receive low-price windows.
        """
        # 2024-01-01 is Monday → we need at least Sat+Sun from the week before
        # Build from 2023-12-25 (Mon) so we have a full prior week of reference data
        data = make_multi_day(
            "2023-12-25",
            n_days=21,
            daily_overrides={
                # Reference sources: inject cheap hour at 10h
                "2023-12-29": {10: 1},  # Friday  → used by Monday 2024-01-01
                "2024-01-01": {10: 1},  # Monday  → used by Tuesday 2024-01-02
                "2024-01-02": {10: 1},  # Tuesday → used by Wednesday 2024-01-03
                "2023-12-30": {10: 1},  # Saturday → used by Saturday 2024-01-06
                "2023-12-31": {10: 1},  # Sunday  → used by Sunday 2024-01-07
            },
        )
        result = calculate_dynamic_network_fee(
            data, use_reference_day=True, **self._base_params()
        )

        def low_hours_on(date_str):
            d = pd.Timestamp(date_str).date()
            rows = result[result["timestamp"].dt.date == d]
            return set(rows[rows["window_type"] == 1]["timestamp"].dt.hour)

        # Monday 2024-01-01 should reflect Friday 2023-12-29 (cheap at 10h)
        assert 10 in low_hours_on("2024-01-01"), (
            "Monday must use previous Friday as reference"
        )

        # Tuesday 2024-01-02 should reflect Monday 2024-01-01 (cheap at 10h)
        assert 10 in low_hours_on("2024-01-02"), (
            "Tuesday must use previous Monday as reference"
        )

        # Wednesday 2024-01-03 should reflect Tuesday 2024-01-02 (cheap at 10h)
        assert 10 in low_hours_on("2024-01-03"), (
            "Wednesday must use previous Tuesday as reference"
        )

        # Saturday 2024-01-06 should reflect Saturday 2023-12-30 (cheap at 10h)
        assert 10 in low_hours_on("2024-01-06"), (
            "Saturday must use previous Saturday (-7 days) as reference"
        )

        # Sunday 2024-01-07 should reflect Sunday 2023-12-31 (cheap at 10h)
        assert 10 in low_hours_on("2024-01-07"), (
            "Sunday must use previous Sunday (-7 days) as reference"
        )

    def test_all_days_in_month_get_windows_except_first_week(self):
        """
        Over a full month with BK4-22-089, every day except those whose
        reference day falls outside the dataset must have at least some
        tagged windows (assuming non-flat prices).
        Days 1-7 may have no reference in dataset; days 8+ must have windows.
        """
        rng = np.random.default_rng(seed=13)
        timestamps = pd.date_range(
            "2024-01-01", periods=96 * 31, freq="15min", tz="UTC"
        )
        prices = rng.uniform(0, 100, len(timestamps))
        data = pd.DataFrame({"timestamp": timestamps, "electricity_price": prices})

        result = calculate_dynamic_network_fee(
            data, use_reference_day=True, **self._base_params()
        )

        for day_offset in range(8, 31):
            d = date(2024, 1, day_offset)
            day_rows = result[result["timestamp"].dt.date == d]
            has_any_window = (day_rows["window_type"] != 0).any()
            assert has_any_window, (
                f"2024-01-{day_offset:02d} has no windows despite being day {day_offset} "
                f"with a reference day well within the dataset"
            )

    def test_predictive_all_days_get_windows(self):
        """
        With use_reference_day=False, every single day uses its own prices,
        so every day must have windows — including day 1. No warm-up period.
        """
        rng = np.random.default_rng(seed=21)
        timestamps = pd.date_range(
            "2024-01-01", periods=96 * 31, freq="15min", tz="UTC"
        )
        prices = rng.uniform(0, 100, len(timestamps))
        data = pd.DataFrame({"timestamp": timestamps, "electricity_price": prices})

        result = calculate_dynamic_network_fee(
            data, use_reference_day=False, **self._base_params()
        )

        for day_offset in range(1, 32):
            d = date(2024, 1, day_offset)
            day_rows = result[result["timestamp"].dt.date == d]
            has_any_window = (day_rows["window_type"] != 0).any()
            assert has_any_window, (
                f"Predictive mode: 2024-01-{day_offset:02d} must have windows "
                f"(no warm-up period needed)"
            )

    def test_at_most_two_windows_per_type_per_day(self):
        """
        Each day must have at most 2 contiguous low-price windows
        and at most 2 contiguous high-price windows.
        This is the direct expression of BK4-22-089's 'up to two peaks per type'
        rule, regardless of how many total slots are tagged.
        """
        rng = np.random.default_rng(seed=55)
        timestamps = pd.date_range(
            "2024-01-01", periods=96 * 14, freq="15min", tz="UTC"
        )
        prices = rng.uniform(0, 100, len(timestamps))
        data = pd.DataFrame({"timestamp": timestamps, "electricity_price": prices})

        result = calculate_dynamic_network_fee(
            data, use_reference_day=False, **self._base_params()
        )

        for day_offset in range(14):
            d = (pd.Timestamp("2024-01-01") + timedelta(days=day_offset)).date()
            day_rows = result[result["timestamp"].dt.date == d].reset_index(drop=True)

            for wtype, label in ((1, "low"), (2, "high")):
                series = (day_rows["window_type"] == wtype).astype(int)
                # A new block starts wherever the series transitions from 0 → 1
                blocks = int((series.diff() == 1).sum())
                # Handle edge case: window starts at very first slot of day
                if series.iloc[0] == 1:
                    blocks += 1
                assert blocks <= 2, (
                    f"2024-01-{day_offset + 1:02d}: found {blocks} {label}-price "
                    f"window blocks — expected at most 2"
                )

    def test_bk4_vs_predictive_low_window_hours_diverge_over_week(self):
        """
        Over a full week where prices shift daily, BK4-22-089 and predictive
        must assign low-price windows to different hours on most days.
        This is the paper's central empirical hypothesis expressed as a test.
        """
        rng = np.random.default_rng(seed=42)
        # Build 2 weeks: week 1 as reference material for BK4, week 2 as test window
        timestamps = pd.date_range(
            "2024-01-01", periods=96 * 14, freq="15min", tz="UTC"
        )
        # Deliberately volatile prices — different daily pattern each day
        prices = np.concatenate(
            [rng.uniform(i * 10, i * 10 + 50, 96) for i in range(14)]
        )
        data = pd.DataFrame({"timestamp": timestamps, "electricity_price": prices})
        params = self._base_params()

        result_bk4 = calculate_dynamic_network_fee(
            data.copy(), use_reference_day=True, **params
        )
        result_pred = calculate_dynamic_network_fee(
            data.copy(), use_reference_day=False, **params
        )

        divergent_days = 0
        for day_offset in range(7, 14):  # test on week 2 only
            d = (pd.Timestamp("2024-01-01") + timedelta(days=day_offset)).date()

            bk4_low = set(
                result_bk4[result_bk4["timestamp"].dt.date == d]
                .pipe(lambda df: df[df["window_type"] == 1])["timestamp"]
                .dt.hour
            )
            pred_low = set(
                result_pred[result_pred["timestamp"].dt.date == d]
                .pipe(lambda df: df[df["window_type"] == 1])["timestamp"]
                .dt.hour
            )

            if bk4_low != pred_low:
                divergent_days += 1

        assert divergent_days >= 4, (
            f"Expected BK4 and predictive to diverge on most days with volatile prices, "
            f"but only {divergent_days}/7 days differed — price patterns may be too similar"
        )

    def test_adjacent_peaks_produce_non_overlapping_tagged_windows(self):
        """
        Two peaks exactly window_size hours apart are both accepted by the
        distance check. Their tagged windows must also be non-overlapping —
        i.e. window 2 must start exactly where window 1 ends.
        This catches the minutes=15 bug in start_offset.
        """
        # Peaks at 08:00 and 14:00 — exactly 6h apart → both accepted
        data = make_multi_day(
            "2024-01-01",
            n_days=2,
            daily_overrides={"2024-01-01": {8: 5, 14: 6}},
        )
        params = {**self._base_params(), "window_size": 6}
        result = calculate_dynamic_network_fee(data, use_reference_day=True, **params)
        jan2 = result[result["timestamp"].dt.date == date(2024, 1, 2)]
        low = jan2[jan2["window_type"] == 1].reset_index(drop=True)

        # Count distinct contiguous blocks
        transitions = low["timestamp"].diff().dt.total_seconds()
        gaps = (transitions > 900).sum()  # gap > 1 interval = new block
        assert len(low) == 2 * WINDOW_SIZE * 4, (
            f"Two adjacent windows must cover exactly {2 * WINDOW_SIZE * 4} slots, got {len(low)}"
        )

        # Window 1 must end at 11:00-1slot=10:45, window 2 must start at 11:00
        boundary = pd.Timestamp("2024-01-02 11:00", tz="UTC")
        assert (low["timestamp"] == boundary).any(), (
            "Slot at 11:00 must be tagged — start of window 2"
        )
        before_w1 = pd.Timestamp("2024-01-02 04:45", tz="UTC")
        assert not (jan2[jan2["timestamp"] == before_w1]["window_type"] == 1).any(), (
            "Slot before window 1 must not be tagged"
        )

    def test_window_size_exactly_matches_tagged_slots(self):
        """Total tagged slots must equal exactly n_peaks * window_size * 4."""
        # Two peaks at known hours (8h and 20h — 12h apart, clearly non-overlapping)
        data = make_multi_day(
            "2024-01-01",
            n_days=2,
            daily_overrides={"2024-01-01": {8: 1, 20: 2}},  # 2 clear min peaks
        )
        window_size = 6
        params = {**self._base_params(), "window_size": window_size}
        result = calculate_dynamic_network_fee(data, use_reference_day=True, **params)
        jan2 = result[result["timestamp"].dt.date == date(2024, 1, 2)]
        low_slots = (jan2["window_type"] == 1).sum()
        expected_slots = 2 * window_size * 4  # 2 peaks × 6h × 4 slots/h = 48

        assert low_slots == expected_slots, (
            f"Expected {expected_slots} slots (2 peaks × {window_size}h × 4), "
            f"got {low_slots}"
        )

    def test_24h_mode_peaks_never_cross_day_boundary(self):
        """
        In 24h mode (no time constraints), the auto-constraint must ensure
        no peak is selected so close to midnight that its window would
        extend into an adjacent calendar day.
        """
        rng = np.random.default_rng(seed=77)
        for _ in range(30):
            timestamps = pd.date_range("2024-03-01 00:00", periods=96, freq="15min")
            df = pd.DataFrame(
                {"timestamp": timestamps, "electricity_price": rng.uniform(0, 100, 96)}
            )
            peaks = select_peaks_no_overlap(
                df,
                WINDOW_SIZE,
                "electricity_price",
                time_window_start=None,
                time_window_end=None,
                kind="min",
            )
            for p in peaks:
                window_start_h = p.hour - WINDOW_SIZE / 2
                window_end_h = p.hour + WINDOW_SIZE / 2
                assert window_start_h >= 0, (
                    f"Peak at {p.hour}h: window starts at {window_start_h}h — "
                    f"crosses into previous day"
                )
                assert window_end_h <= 24, (
                    f"Peak at {p.hour}h: window ends at {window_end_h}h — "
                    f"crosses into next day"
                )

    def test_start_hour_zero_not_excluded(self):
        """
        time_window_start=0 must NOT be treated as falsy (Python bool(0) = False).
        With start=0, peaks at hour 2 ARE eligible.
        With start=None (24h auto-constraint, window_size=6), effective_start=3,
        so hour 2 is NOT eligible — proving the two modes behave differently.
        """
        day = make_day(price_overrides={2: 5, 10: 6, 18: 7})

        peaks_explicit_zero = select_peaks_no_overlap(
            day,
            WINDOW_SIZE,
            "electricity_price",
            time_window_start=0,
            time_window_end=21,
            kind="min",
        )
        peaks_auto = select_peaks_no_overlap(
            day,
            WINDOW_SIZE,
            "electricity_price",
            time_window_start=None,
            time_window_end=None,
            kind="min",
        )
        # start=0 → hour 2 eligible
        assert 2 in get_peak_hours(peaks_explicit_zero), (
            "time_window_start=0 must not be falsy — hour 2 must be reachable"
        )
        # None → auto effective_start=3 → hour 2 NOT eligible
        assert 2 not in get_peak_hours(peaks_auto), (
            "24h auto-constraint effective_start=3 must exclude hour 2"
        )

    def test_none_constraints_allow_early_morning_selection(self):
        """
        In 24h mode (None), the auto-constraint allows peaks from effective_start
        (= window_size/2) onward — earlier than the default 6h constraint.
        A peak at hour 4 is reachable with None but not with start=6.
        """
        # With window_size=6: effective_start=3 → hour 4 is within [3, 21]
        day = make_day(price_overrides={4: 5, 14: 6})

        peaks_no_constraint = select_peaks_no_overlap(
            day,
            WINDOW_SIZE,
            "electricity_price",
            time_window_start=None,
            time_window_end=None,
            kind="min",
        )
        peaks_6_21 = select_peaks_no_overlap(
            day,
            WINDOW_SIZE,
            "electricity_price",
            time_window_start=6,
            time_window_end=21,
            kind="min",
        )
        assert 4 in get_peak_hours(peaks_no_constraint), (
            "Hour 4 must be reachable in 24h mode (effective_start=3)"
        )
        assert 4 not in get_peak_hours(peaks_6_21), (
            "Hour 4 must be excluded by explicit time_window_start=6"
        )

    def test_boundary_peak_window_capped_at_end_of_day(self):
        """
        In 24h mode, a peak at the latest allowed hour (effective_end = 24 - window_size/2)
        produces a window that ends exactly at midnight — capped cleanly at 23:45,
        no timestamps from the next day are tagged.
        """
        # window_size=6: effective_end=21 → peak at 21:00 → window [18:00, 00:00)
        data = make_multi_day(
            "2024-01-01",
            n_days=1,
            daily_overrides={"2024-01-01": {21: 1}},
        )
        params = {
            **self._base_params(),
            "time_window_start": None,
            "time_window_end": None,
            "window_size": 6,
        }
        result = calculate_dynamic_network_fee(data, use_reference_day=False, **params)
        # 23:45 must be tagged
        last_slot = result[result["timestamp"].dt.strftime("%H:%M") == "23:45"]
        assert (last_slot["window_type"] == 1).any(), (
            "23:45 must be tagged — window ends at midnight, capped to 23:45"
        )

        # No next-day timestamps should exist (only 1 day of data)
        assert result["timestamp"].dt.date.nunique() == 1, (
            "No next-day spillover — auto-constraint prevents midnight crossing"
        )
