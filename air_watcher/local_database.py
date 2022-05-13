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
import copy
import collections.abc
import sqlite3
import os
import logging
import json
import sys
from functools import reduce
from datetime import date, datetime, time, timedelta

logger = logging.getLogger(__name__)


def deep_get(dictionary, keys, default=None):
    """
    Gets a nested dictionary or, if it does not exists gives the default.

    Big downside of this is that the dictionary key has to be a string, as json can only have string as dictionary this
    might be for the best, as int or float as key might create some confusion when handling json-files.

    Stolen here: https://stackoverflow.com/a/46890853

    :param dict dictionary: a dictionary of any depth
    :param str keys: path to the variable, seperated by '|' per level
    :param any default: default value given if key cannot be found
    """
    return reduce(lambda d, key: d.get(key, default) if isinstance(d, dict) else default, keys.split("|"), dictionary)


def deep_set(value, keys: str) -> dict:
    """
    returns a deeply nested dictionary with the keys provided

    Note, normally I would recommend using parameter unpacking with *keys here but this is the inverse of the above
    deep_get function therefore this implementation is used.

    :param any value: the value you want to have set in the depths
    :param str keys: keys seperated by '|' (basically the reverse of deep_get)
    :returns: a dictionary with the set keys
    :rtype: dict
    """
    # this looks rather clunky, there must be something more...sleek
    key_path = keys.split("|")
    value = copy.deepcopy(value)  # in case value is a dictionary or something else by reference
    if not keys:
        return value
    else:
        for key in reversed(key_path):
            value = {key: value}
    return value


def deep_update(d, u):
    """
    Part 2 of my unncessary complex setup

    Stolen from here:
    https://stackoverflow.com/a/3233356

    :param dict d: dictionary that will get updated by u
    :param any u: any one variable that will be integrated into d, might be a dictionary
    :returns: nothing, dictionary will be updated by reference
    """
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d

data_mapping = {
    'gas_oxidising': "gas|oxidising",
    'gas_reducing': "gas|reducing",
    'gas_nh3': "gas|nh3",
    'particles_1_0':  "particles|m3|atmo|1.0",
    'particles_2_5':  "particles|m3|atmo|2.5",
    'particles_10_0': "particles|m3|atmo|10",
    'weather_temperature': "weather|temperature",
    'weather_pressure': "weather|pressure",
    'weather_humidity': "weather|humidity",
    'light_lux': "light|lux",
    'light_ir': "light|ir",
    'noise_1': "noise|20-1K",
    'noise_2': "noise|1K-3K",
    'noise_3': "noise|3K-8K",
    'co2': "gas|co2"  # currently, not even implemented but I got the sensor
}


class LocalCache:
    def __init__(self, db_path):
        if not os.path.exists(db_path):
            self.db = sqlite3.connect(db_path)
            self.cur = self.db.cursor()
            self.init_database()
            self.db.close()
        try:
            self.db = sqlite3.connect(f"file:{db_path}?mode=rw", uri=True)
            self.db.row_factory = sqlite3.Row  # different access mode
            self.cur = self.db.cursor()
        except sqlite3.OperationalError as err:
            logger.error(f"Database operation error: {err}")
            raise  # I cannot actually let the instantiation fail so forwarding the exception it is

    def export(self, export_format="json", time_depth=604800):
        pass

    def insert_block(self, raw_data: dict, synthetic_date=None):
        """
        Inserts the output of one .get_all() into the database, or synthetic data with blanks, procdure does not
        care, will use datetime.today() of the local system for timestamp if not otherwise stated

        :param dict raw_data: assumed output of .get_all() from the sensor library, will use data_mapping as key
        :param datetime synthetic_date: if set overwrites default .today() with the provided timestamp
        """
        query = """
            INSERT INTO sensor_data (
                timepoint, gas_oxidising, gas_reducing, gas_nh3, particles_1_0, particles_2_5, particles_10_0,
                weather_temperature, weather_pressure, weather_humidity, light_lux, light_ir, noise_1, noise_2, noise_3,
                co2)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        # my one-liner sense tingles, but I cant be bothered
        if synthetic_date and isinstance(synthetic_date, datetime):
            inserts = [synthetic_date]
        else:
            inserts = [datetime.now()]  # I once read that a list is a collection of similar items, well about that...
        for key, path in data_mapping.items():
            inserts.append(deep_get(raw_data, path))
        try:
            self.cur.execute(query, tuple(inserts))
            self.db.commit()
        except ValueError:
            logging.error("Value Error, test, delete this")

    def insert_bulk(self, raw_data_list: dict):
        """
        Inserts a more than one entry into the database of the format:
        "isoformat-data": { key: value }
        I am not entirely sure if it is any better than just doing single executes 20 times

        *WARNING* : this uses datetime.fromisoformat() to parse the 'iso' strings which is only the inverse of
        datetime.isostring() and does not accept a wide range and might fail with 3rd party iso-strings

        This might be aswell:
        `for key, raw_data in raw_data_list():`
        `    my_db.insert_block(raw_data, synthetic_date=datetime.fromisoformat(key))`
        """
        query = """
            INSERT INTO sensor_data (
                timepoint, gas_oxidising, gas_reducing, gas_nh3, particles_1_0, particles_2_5, particles_10_0,
                weather_temperature, weather_pressure, weather_humidity, light_lux, light_ir, noise_1, noise_2, noise_3,
                co2)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        date_errors = 0
        inserts = []
        # preps a list with all the data in it
        for key, value in raw_data_list.items():
            try:
                temp_date = datetime.fromisoformat(key)
            except ValueError:
                date_errors += 1
                continue
            one_line = [temp_date]
            for prop, path in data_mapping.items():
                one_line.append(deep_get(value, path))
            inserts.append(tuple(one_line))
        try:
            self.cur.executemany(query, inserts)
            self.db.commit()
        except sqlite3.OperationalError as e:
            logger.error(f"LocalCache.insert_bulk() failed with exception: {e}")
            return False
        if date_errors > 0:
            logger.warning(f"There were {date_errors} parsing errors of iso strings")
        return True

    def fetch_by_exact_date(self, target_date: datetime) -> dict:
        """
        Fetches exactly one entry by an exact datetime (down to the millisecond)

        :param datetime target_date: the point of time you want the data from
        :returns: Either None if nothing was found or a dictionary containing all available data
        :rtype: None or dict
        """
        query = """SELECT timepoint, gas_oxidising, gas_reducing, gas_nh3, particles_1_0, particles_2_5, particles_10_0,
                    weather_temperature, weather_pressure, weather_humidity, light_lux, light_ir, noise_1, noise_2,
                    noise_3, co2 
                FROM sensor_data 
                WHERE timepoint = ? 
                LIMIT 1"""
        self.cur.execute(query, [target_date])
        raw_data = self.cur.fetchone()
        return LocalCache._row_to_transfer_format(raw_data)

    def fetch_by_aoe_date(self, target_date: datetime, aoe: int) -> dict:
        """
        Fetches as many entries as possible in the given time intervall, convinience function that does math for you
        and then calls fetch_by_range()

        :param datetime target_date: approximated middle point of the time of interest
        :param int aoe: time in seconds, seen as 'diameter' with the target_date as middle, therefore you get the date range (target_date-aoe/2) --- (target_date+aoe/2)
        :returns: a dictionary with the format { 'iso_string' : {'data_a': {}, 'data_b': {}, ...}, 'iso_string': ....}
        """
        # calculate time radius
        delta = timedelta(seconds=int(aoe/2))
        past = target_date-delta
        future = target_date+delta
        return self.fetch_by_range(past, future)

    def fetch_by_range(self, past: datetime, future: datetime):
        """
        Fetches as many entries as possible for the given intervall
        :param datetime past: earlierst point in time you want data from, precise to the millisecond
        :param datetime future: latest point in t ime you want data from
        :returns: a dictionary with the format { 'iso_string' : {'data_a': {}, 'data_b': {}, ...}, 'iso_string': ....}
        """
        query = """SELECT 
                        timepoint, gas_oxidising, gas_reducing, gas_nh3, particles_1_0, particles_2_5, particles_10_0,
                        weather_temperature, weather_pressure, weather_humidity, light_lux, light_ir, noise_1, noise_2, 
                        noise_3, co2 
                    FROM sensor_data 
                    WHERE timepoint > ? AND timepoint < ?"""
        # db call
        self.cur.execute(query, (past, future))
        rows = self.cur.fetchall()
        # data processing
        result = {}
        for raw_data in rows:
            result.update(LocalCache._row_to_transfer_format(raw_data))
        return result

    @staticmethod
    def _row_to_transfer_format(raw_data):
        data_point = {}
        for key in raw_data.keys():  # possible because row factory
            if key in data_mapping:
                if raw_data[key] is None:
                    continue
                deep_update(data_point, deep_set(raw_data[key], data_mapping[key]))
        return {raw_data['timepoint']: data_point}

    def delete_by_date(self, target_date: datetime):
        """
        Attempts to delete all timepoints with the exact ISO Date, to the millisecond
        """
        query = """DELETE FROM sensor_data WHERE timepoint = ? """
        self.db.execute(query, [target_date])

    def delete_by_date_range(self, start_date: datetime, stop_data: datetime):
        pass

    def delete_by_data_aoe(self, target_date: datetime, aoe: int):
        pass

    def fill_from_json(self, json_file_path: str):
        """
        Puts all the data from a normalized json file into this database, will create duplicates without looking back

        :param str json_file_path: Path to a properly formatted json
        """
        with open(json_file_path, "r") as json_in:
            try:
                raw = json.load(json_in)
            except json.JSONDecodeError as e:
                logging.error(f"LocalCache>fill_from_json: json decode error: {e:120}")
                return False
            self.insert_bulk(raw)
            # for key, raw_data in raw.items():
            #    my_db.insert_block(raw_data, synthetic_date=datetime.fromisoformat(key))
        return True

    def close(self):
        self.db.close()

    def init_database(self):
        query = """
            CREATE TABLE IF NOT EXISTS sensor_data (
                uid INTEGER PRIMARY KEY AUTOINCREMENT,
                timepoint TIMESTAMP NOT NULL,
                gas_oxidising REAL,
                gas_reducing REAL,
                gas_nh3 REAL,
                particles_1_0 INTEGER,
                particles_2_5 INTEGER,
                particles_10_0 INTEGER,
                weather_temperature REAL,
                weather_pressure REAL,
                weather_humidity REAL,
                light_lux REAL,
                light_ir REAL,
                noise_1 REAL,
                noise_2 REAL,
                noise_3 REAL,
                co2 REAL
            );"""
        self.db.execute(query)


if __name__ == "__main__":

    logger.info("local_database: main called, accepts 1 args: [fill] (deletes local.db and fills it with values.json)")
    my_db = LocalCache("./local_cache.db")

    print(sys.argv)
    if sys.argv[1] == "fill":
        logger.warning("filling local.db")
        my_db.fill_from_json("./values.json")
    bla = my_db.fetch_by_aoe_date(datetime.combine(date.today(), time(12, 0, 0)), 3600*24)
    print(bla)

