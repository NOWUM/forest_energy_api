# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
This package contains the CRUD operations (CREATE, READ, UPDATE, DELETE) for each repository/table in database.
"""

from .grid import grid
from .process_electricity import process_electricity
from .process_heat import process_heat
from .emissions import emissions
from .model import model
from .footprint import footprint
from .data_parc import data_parc
from .flexible_power import flexible_power
from .optimization_results import optimization_results
from .prices import prices
from .simulation_input_data import simulation_input_data
