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

from sensors import SensorBundle
from local_database import LocalCache
import logging
import json
import os
import datetime

save_path = "values.json"

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S',
    filename="sensors.log")

if __name__ == "__main__":
    logging.info("Waking up, priming sensors...")
    sensor = SensorBundle(warmup_cycles=15)
    logging.info(f"Sensors ready, warming up {sensor.warmup_cycles} times, then reading")
    all_raw = sensor.get_all(condensed=True)

    now = datetime.datetime.now()
    history = {}
    if os.path.isfile(save_path):
        with open(save_path, "r") as save_game:
            try:
                history = json.load(save_game)
            except json.JSONDecodeError:
                history = {}
    with open(save_path, "w") as save_game:
        history[now.isoformat()] = all_raw
        json.dump(history, save_game, indent=2)
    logging.info(f"Writing to {save_path} completed, new len is {len(history)}")
    db_path = "local_cache.db"
    logging.info(f"Experimental Database Connection to {db_path}")
    db = LocalCache(db_path)
    db.insert_block(all_raw, now)
    logging.info(json.dumps(all_raw['particles']['m3']['atmo'], indent=2))
    db.close()

