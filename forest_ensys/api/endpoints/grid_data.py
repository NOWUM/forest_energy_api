# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Text

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from forest_ensys import crud, schemas
from forest_ensys.api import deps
from forest_ensys.api.endpoints import footprint_data, emissions_data
from datetime import datetime, timedelta
from forest_ensys.core import crawlers
import pandas as pd
import logging
from typing import Optional, Dict, Any

from sqlalchemy.exc import SQLAlchemyError

# Setup logging
logger = logging.getLogger(__name__)
router = APIRouter()

keys = {
    # 411: 'Prognostizierter Stromverbrauch',
    # 410: 'Realisierter Stromverbrauch',
    4169: "Preis",
    4066: "Biomasse",
    1226: "Wasserkraft",
    1225: "Wind Offshore",
    4067: "Wind Onshore",
    4068: "Photovoltaik",
    1228: "Sonstige Erneuerbare",
    1223: "Braunkohle",
    4071: "Erdgas",
    4070: "Pumpspeicher",
    1227: "Sonstige Konventionelle",
    4069: "Steinkohle",
    # 5097: 'Prognostizierte Erzeugung PV und Wind Day-Ahead'
}

grid_to_factors = {
    "Biomasse": "biomass",
    "Wasserkraft": "hydro",
    "Wind Offshore": "wind",
    "Wind Onshore": "wind",
    "Photovoltaik": "solar",
    "Braunkohle": "coal",
    "Steinkohle": "coal",
    "Erdgas": "gas",
    "Sonstige Konventionelle": "gas",
    "Sonstige Erneuerbare": "solar",
    "Pumpspeicher": "hydro",
}

DAY_AHEAD_COMMODITY_ID = 4169

@router.delete(
    "/",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {"message": "Grid data table deleted successfully"}
                }
            },
        }
    },
)
def delete_grid_data(db: Session = Depends(deps.get_db)) -> Text:
    """
    Delete all grid data
    """
    crud.grid.delete(db=db)
    crud.prices.delete(db=db, source="smard")
    crud.footprint.delete(db=db)
    raise HTTPException(status_code=200, detail="Grid data table deleted successfully")


@router.get("/", response_model=List[schemas.Grid])
def get_all_grid_data(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> List[schemas.Grid]:
    """
    Retrieve all grid data
    """
    grid_data = crud.grid.get_multi(db=db, skip=skip, limit=limit)
    return grid_data

def calculate_start_timestamps(
    latest: Optional[datetime], default_start_date: str
) -> tuple[datetime, datetime]:
    """
    Calculate start timestamps for SMARD API.

    SMARD API quirk: Data is organized in weekly chunks starting Sunday 22:00 UTC.
    We need to align our start date to the most recent Sunday 22:00 to avoid gaps.
    """
    if latest is None:
        latest = pd.to_datetime(default_start_date)
        latest = latest.replace(tzinfo=None)  # Ensure naive for processing

    # SMARD data starts Sunday 22:00 UTC (or 21:45 in some cases)
    # If latest is not Sunday after 22:00, backtrack to last Sunday 22:00
    if latest.weekday() != 6 or (
        latest.hour < 22 or (latest.hour == 21 and latest.minute < 45)
    ):
        days_since_sunday = (latest.weekday() + 1) % 7
        last_sunday = latest - timedelta(days=days_since_sunday)
        last_sunday = last_sunday.replace(hour=22, minute=0, second=0, microsecond=0)
        logger.info(
            f"Adjusting start date from {latest} to last Sunday 22:00: {last_sunday}"
        )
        latest = last_sunday

    # Handle 21:45 vs 22:45 cases (SMARD API inconsistency)
    if latest.hour == 21 and latest.minute == 45:
        timestamp1 = latest.replace(hour=22, minute=0, second=0, microsecond=0)
        timestamp2 = latest.replace(hour=23, minute=0, second=0, microsecond=0)
    else:
        timestamp1 = latest.replace(hour=23, minute=0, second=0, microsecond=0)
        timestamp2 = latest.replace(hour=22, minute=0, second=0, microsecond=0)

    return timestamp1, timestamp2


def is_commodity_up_to_date(
    commodity_id: int, latest_timestamp: datetime, staleness_hours: int = 6
) -> bool:
    """
    Check if commodity data is up-to-date.

    Day-ahead prices (4169): Available 24h in advance, check if we have tomorrow's data
    Real-time data: Check if within last N hours
    """
    now = datetime.now(tz=latest_timestamp.tzinfo)

    if commodity_id == DAY_AHEAD_COMMODITY_ID:
        # For day-ahead: Check if we have data for tomorrow
        # Day-ahead published around 13:00 CET daily
        if latest_timestamp.date() > now.date():
            logger.info(
                f"Commodity {commodity_id} up-to-date (has future data: {latest_timestamp.date()})"
            )
            return True
        # If before 14:00 CET and we have today's data, consider it current
        if now.hour < 14 and latest_timestamp.date() >= now.date():
            logger.info(
                f"Commodity {commodity_id} up-to-date (before 14:00, has today's data)"
            )
            return True
    else:
        # For real-time data: Check if within staleness window
        if latest_timestamp > now - timedelta(hours=staleness_hours):
            logger.info(
                f"Commodity {commodity_id} up-to-date (within {staleness_hours}h)"
            )
            return True

    return False


def update_grid_data_logic(
    db: Session, keys: Dict[int, str], default_start_date: str = "12-31-2023 22:00:00"
) -> Dict[str, Any]:
    """
    Core logic for updating grid data (separated from endpoint).
    This can be called from an endpoint, background task, or scheduled job.
    """
    try:
        latest_emissions_factors = get_latest_emissions_factors(db=db)
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving emissions factors: {e}")
        raise HTTPException(
            status_code=502, detail="Could not retrieve emissions data from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving emissions factors: {e}")
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve emissions data. Server probably offline",
        )

    commodities_updated = {}
    max_iterations = 10  # Safety limit instead of infinite loop
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        logger.info(f"Update iteration {iteration}/{max_iterations}")

        for commodity_id, commodity_name in keys.items():
            # Get latest timestamp for this commodity
            try:
                if commodity_id != DAY_AHEAD_COMMODITY_ID:
                    latest = crud.grid.get_latest_for_commodity(
                        db=db, commodity_id=commodity_id
                    )
                else:
                    latest = crud.prices.get_latest(db=db)
            except SQLAlchemyError as e:
                logger.error(f"Database error for commodity {commodity_id}: {e}")
                continue

            latest_in_db = None
            latest_dt = None

            try:
                if latest:
                    latest_dt = pd.to_datetime(latest.timestamp)
                    # Ensure timezone-aware
                    if latest_dt.tzinfo is None:
                        latest_in_db = latest_dt.tz_localize("UTC")
                    else:
                        latest_in_db = latest_dt

                    logger.info(
                        f"Latest in DB for commodity {commodity_id}: {latest_in_db}"
                    )

                    # Check if this commodity is up-to-date
                    if is_commodity_up_to_date(commodity_id, latest_in_db):
                        commodities_updated[commodity_id] = True
                        continue  # Skip to next commodity

                # Calculate start timestamps (handles SMARD quirks)
                timestamp1, timestamp2 = calculate_start_timestamps(
                    latest_dt, default_start_date
                )

            except (ValueError, AttributeError) as e:
                logger.warning(
                    f"Using default start date for commodity {commodity_id}: {e}"
                )
                timestamp1, timestamp2 = calculate_start_timestamps(
                    None, default_start_date
                )

            # Convert to Unix milliseconds
            start_date_unix = int(timestamp1.timestamp() * 1000)
            second_start_date_unix = int(timestamp2.timestamp() * 1000)

            # Fetch data from SMARD API
            data_for_commodity = crawlers.get_data_per_commodity(
                commodity_id, commodity_name, start_date_unix, second_start_date_unix
            )

            if data_for_commodity.empty:
                logger.warning(f"No new data available for commodity {commodity_id}")
                # Mark as updated to avoid infinite retries
                commodities_updated[commodity_id] = True
                continue

            # Remove duplicate timestamps
            data_for_commodity = data_for_commodity[
                ~data_for_commodity.index.duplicated(keep="first")
            ]

            # Filter out already-stored data
            if latest_in_db is not None:
                data_for_commodity = data_for_commodity[
                    data_for_commodity["timestamp"] > latest_in_db
                ]

            if data_for_commodity.empty:
                logger.info(f"All data already in DB for commodity {commodity_id}")
                commodities_updated[commodity_id] = True
                continue

            # Store in database
            try:
                if commodity_id == DAY_AHEAD_COMMODITY_ID:
                    data_for_commodity = data_for_commodity.rename(
                        columns={"mwh": "price"}
                    )
                    data_for_commodity["source"] = "smard"
                    data_for_commodity = data_for_commodity.drop(
                        columns=["commodity_id", "commodity_name"], errors="ignore"
                    )
                    crud.prices.create_multi(
                        db, obj_in=data_for_commodity.to_dict(orient="records")
                    )
                else:
                    data_for_commodity["co2"] = (
                        data_for_commodity["mwh"]
                        * latest_emissions_factors.get(commodity_name, 0)
                        * 1000
                    )
                    crud.grid.create_multi(
                        db, obj_in=data_for_commodity.to_dict(orient="records")
                    )

                logger.info(
                    f"Stored {len(data_for_commodity)} records for commodity {commodity_id}"
                )
            except SQLAlchemyError as e:
                logger.error(f"Database error storing commodity {commodity_id}: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to store data for commodity {commodity_id}",
                )

        # Check if all commodities are updated
        if len(commodities_updated) == len(keys):
            logger.info("All commodities up-to-date")
            break

    # Update footprint data
    try:
        footprint_data.update_footprint_data(db)
    except Exception as e:
        logger.error(f"Error updating footprint data: {e}")
        # Don't fail the whole operation for this

    return {
        "commodities_updated": len(commodities_updated),
        "total_commodities": len(keys),
        "iterations": iteration,
    }


@router.post(
    "/update",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {"message": "Grid data updated successfully"}
                }
            },
        },
        502: {
            "description": "Server Error",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Could not retrieve emissions data. Server probably offline"
                    }
                }
            },
        },
        404: {
            "description": "Not Found",
            "content": {
                "application/json": {
                    "example": {"message": "Website did not return any data."}
                }
            },
        },
    },
)
def update_recent_grid_data(
    db: Session = Depends(deps.get_db),
    default_start_date: str = Query(
        "12-31-2023 22:00:00",
        description="If the database is empty, this is the start date for data fetching.",
    ),
):
    """
    Trigger grid data update.

    """
    try:
        result = update_grid_data_logic(db, keys, default_start_date)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "message": "Grid data updated successfully",
                **result,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during grid data update")
        raise HTTPException(
            status_code=500, detail=f"Grid data update failed: {str(e)}"
        )


def get_latest_emissions_factors(db: Session) -> dict:
    emissions = {}
    if not crud.emissions.get_multi(db=db):
        print("Emissions data seems empty, trying to crawl")
        emissions_data.update_emissions_data(db=db)

    for commodity_id, commodity_name in keys.items():
        if commodity_id == 4169:
            continue
        print(
            f"getting latest emission factor for {commodity_name} and {grid_to_factors[commodity_name]}"
        )
        specific_emission = crud.emissions.get_specific_emissions(
            db=db,
            zone_key="DE",
            emission_type="direct",
            production_mode=grid_to_factors[commodity_name],
        )
        print(specific_emission)
        emissions[commodity_name] = specific_emission.value
    return emissions
