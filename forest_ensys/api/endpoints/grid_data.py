# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Text

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from forest_ensys import crud, model, schemas
from forest_ensys.api import deps
from forest_ensys.api.endpoints import footprint_data, emissions_data

from forest_ensys.core import crawlers
import pandas as pd
from datetime import timedelta

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
    crud.prices.delete(db=db)
    crud.footprint.delete(db=db)
    raise HTTPException(
        status_code=200, detail="Grid data table deleted successfully"
    )

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

@router.get("/update", responses={
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
            }
        },
        404: {
            "description": "Not Found",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Website did not return any data."
                    }
                }
            }
        }   
    }
)
def update_recent_grid_data(db: Session = Depends(deps.get_db)):
    """
    Retrieve the most recent grid data
    """
    while True:
        grid_data = []
        prices = []
        start_date = "12-31-2023 22:00:00"
        try:
            latest_emissions_factors = get_latest_emissions_factors(db=db)
        except Exception:
            raise HTTPException(
                status_code=502,
                detail="Could not retrieve emissions data. Server probably offline",
            )
        for commodity_id, commodity_name in keys.items():
            if commodity_id != 4169:
                latest = crud.grid.get_latest_for_commodity(db=db, commodity_id=commodity_id)
            else:
                latest = crud.prices.get_latest(db=db)
            latest_in_db = None
            try:
                latest = pd.to_datetime(latest.timestamp)
                latest_in_db = latest.tz_localize("UTC")
                print(f"The latest date in the database is {latest}")
                if latest.weekday() != 6 or (latest.hour < 21 and latest.minute == 45):
                    last_sunday = latest - timedelta(days=(latest.weekday() + 1) % 7)
                    print(
                        f"the latest date in the database is not a sunday after 22:00, taking last week sunday 22:00 as start date to fill the missing data: {latest} -> {last_sunday}"
                    )
                    latest = last_sunday
                if latest.hour == 21 and latest.minute == 45:
                    print(
                        "the latest date in the database is a sunday 21:45, taking this sunday 22:00 as start date"
                    )
                    latest = latest.replace(hour=22, minute=0, second=0, microsecond=0)
                    latest2 = latest.replace(hour=23, minute=0, second=0, microsecond=0)
                else:
                    print(
                        "the latest date in the database is a sunday 22:45, taking this sunday 23:00 as start date"
                    )
                    latest = latest.replace(hour=23, minute=0, second=0, microsecond=0)
                    latest2 = latest.replace(hour=22, minute=00, second=0, microsecond=0)
            except Exception as e:
                print(f"Using the default start date for commodity {commodity_id, e}")
                latest = pd.to_datetime(start_date)
                latest2 = latest.replace(hour=23, minute=0, second=0, microsecond=0)

            start_date_unix = int(latest.timestamp() * 1000)
            second_start_date_unix = int(latest2.timestamp() * 1000)
            data_for_commodity = crawlers.get_data_per_commodity(
                commodity_id, commodity_name, start_date_unix, second_start_date_unix
            )
            if data_for_commodity.empty:
                raise HTTPException(
                    status_code=404, detail="Could not get data for commodity {commodity_id}"
                )
            # if data_for_commodity is None:
            #    return HTTPException(status_code=404, detail="Could not reach website for crawling data")
            # delete timezone duplicate
            # https://stackoverflow.com/a/34297689
            data_for_commodity = data_for_commodity[
                ~data_for_commodity.index.duplicated(keep="first")
            ]
            if latest_in_db is not None:
                data_for_commodity = data_for_commodity[
                    data_for_commodity["timestamp"] > latest_in_db
                ]
            if commodity_id == 4169:
                for index, row in data_for_commodity.iterrows():
                    db_obj = model.Prices(
                        timestamp=row["timestamp"],
                        price=row["mwh"],
                        source="smard"
                    )
                    prices.append(db_obj)
            else:
                for index, row in data_for_commodity.iterrows():
                    db_obj = model.Grid(
                        timestamp=row["timestamp"],
                        commodity_id=row["commodity_id"],
                        commodity_name=row["commodity_name"],
                        mwh=row["mwh"],
                        co2=row["mwh"] * latest_emissions_factors[commodity_name] * 1000,
                    )
                    grid_data.append(db_obj)
        crud.grid.create_multi(db=db, obj_in=grid_data)
        crud.prices.create_multi(db=db, obj_in=prices)
        footprint_data.update_footprint_data(db)
    raise HTTPException(
            status_code=200, detail="Grid data updated successfully"
        )

def get_latest_emissions_factors(db: Session) -> dict:
    emissions = {}
    if not crud.emissions.get_multi(db=db):
        print("Emissions data seems empty, trying to crawl")
        emissions_data.update_emissions_data()

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