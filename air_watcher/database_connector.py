#!/usr/bin/env python3
# coding: utf-8

# Copyright 2021 by BurnoutDV, <development@burnoutdv.com>
#
# This file is part of AirWatcher.
#
# AirWatcher is free software: you can redistribute
# it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# AirWatcher is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# @license GPL-3.0-only <https://www.gnu.org/licenses/gpl-3.0.en.html>

import json
import mysql.connector as db

class DatabaseHandler:
    def __init__(self, config_path: str, username=None, password=None, database=None):
        settings = {}
        if config_path:
            with open(config_path, "r") as conf_fh:
                settings = json.load(conf_fh)  # i was about to write exception handling, no, when it fails it fails
        # direct parameters have priority over setting file
        for attr in ['username', 'password', 'database']:
            if not getattr(self, attr) and attr in settings:
                setattr(self, attr, settings[attr])
            locals()
        self.connection = db.connect(
            user=username,
            password=password,
            host="localhost",
            database=database
        )
