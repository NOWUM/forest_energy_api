# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
This package contains every model that is returned from the Rest-API.
"""

from .user import User, UserCreate, UserInDB, UserUpdate
from .token import Token, TokenPayload
from .grid import Grid, GridCreate, GridUpdate
from .process_electricity import (
    ProcessElectricity,
    ProcessElectricityCreate,
    ProcessElectricityUpdate,
)
from .process_heat import ProcessHeat, ProcessHeatCreate, ProcessHeatUpdate
from .emissions import Emissions, EmissionsCreate, EmissionsUpdate
from .co2 import Co2
from .model import Model, ModelCreate, ModelUpdate
from .footprint import Footprint, FootprintCreate, FootprintUpdate
from .data_parc import DataParc, DataParcCreate, DataParcUpdate
from .optimization_results import OptimizationResult
from .prices import Prices
from .flexible_power import FlexiblePower, FlexiblePowerCreate, FlexiblePowerUpdate
