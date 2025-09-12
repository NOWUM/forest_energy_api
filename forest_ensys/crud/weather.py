# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from forest_ensys.core import crawlers
from forest_ensys.crud.base import CRUDBase
from forest_ensys.model import Weather
from forest_ensys.schemas import WeatherCreate, WeatherUpdate


class CRUDWeather(CRUDBase(Weather, WeatherCreate, WeatherUpdate)):
    def get_current_weather(self, db: Session) -> Optional[Weather]:
        latest = db.query(Weather).order_by(desc(Weather.timestamp)).first()
        return db.query(Weather).filter(Weather.timestamp == latest.timestamp)

    def create(self, db: Session) -> Optional[Weather]:
        db.add_all(crawlers.crawl_weather_data())
        db.commit()
        return db.query(Weather).order_by(desc(Weather.timestamp)).first()


grid = CRUDWeather(Weather)
