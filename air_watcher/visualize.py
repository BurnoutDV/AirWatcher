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

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date, datetime, time, timedelta
import json
import logging
import os
import sys


logger = logging.getLogger(__name__)

# per https://matplotlib.org/stable/tutorials/introductory/usage.html#sphx-glr-tutorials-introductory-usage-py


"""
This is a rather useless piece of software, just see it as set of scripts to quickly asses data and visualize some
of it. This is actually the first time i ever touched matplot lib and its definetly not needed for this project but
i wanted to see the values i got from my first set of scripts. For now this is hardcoded to only displays value of
today
"""


def plot_weather(raw_values: dict, output="weather.png", day_only=True, dpi=300):
    weather_over_time = {}
    for iso_data in raw_values:
        that_date = datetime.fromisoformat(iso_data)
        weather_over_time[that_date] = raw_values[iso_data]['weather']

    fig, ax1 = plt.subplots()
    ax1.set_xlabel("Time")
    plt.xticks(rotation=45)
    ax1.set_ylabel("Temperature C /Humidity %")
    ax1.set_title("Temperature over Time")

    ax2 = ax1.twinx()
    ax2.set_ylabel("Pressure hPa")

    times = [y for y in weather_over_time.keys()]

    l1, = ax1.plot([y for y in weather_over_time.keys()], [x['temperature'] for x in weather_over_time.values()], color="r")
    l2, = ax2.plot([y for y in weather_over_time.keys()], [x['pressure'] for x in weather_over_time.values()], color="b")
    l3, = ax1.plot([y for y in weather_over_time.keys()], [x['humidity'] for x in weather_over_time.values()], color="g")

    ax1.legend([l1, l3], ["Temperature", "Humidity"])
    ax2.legend([l2], ['Pressure'], loc="lower left")
    if day_only:
        xformatter = mdates.DateFormatter('%H:%M')
        plt.gcf().axes[0].xaxis.set_major_formatter(xformatter)
    plt.savefig(output, dpi=dpi)


def plot_particles(raw_values: dict, output="particles.png", day_only=True, dpi=300):
    particles_over_time = {}
    for iso_data in raw_values:
        that_date = datetime.fromisoformat(iso_data)
        if 'particles' in raw_values[iso_data]:
            particles_over_time[that_date] = raw_values[iso_data]['particles']['m3']['atmo']

    fig, ax = plt.subplots()
    ax.set_xlabel("Time")
    plt.xticks(rotation=45)
    ax.set_ylabel("n Particles")
    ax.set_title("Particles per size overtime")

    times = [y for y in particles_over_time.keys()]

    l1, = ax.plot(times, [x['1.0'] for x in particles_over_time.values()])
    l2, = ax.plot(times, [x['2.5'] for x in particles_over_time.values()])
    l3, = ax.plot(times, [x['10'] for x in particles_over_time.values()])
    ax.legend([l1, l2, l3], [
        "PM1.0 ug/m3 (ultrafine particles)",
        "PM2.5 ug/m3 (combustion particles, organic compounds, metals)",
        "PM10 ug/m3  (dust, pollen, mould spores)"
    ])
    if day_only:
        xformatter = mdates.DateFormatter('%H:%M')
        plt.gcf().axes[0].xaxis.set_major_formatter(xformatter)
    plt.savefig(output, dpi=dpi)


def plot_gas(raw_values, output="gases.png", day_only=True, dpi=300):
    gases_over_time = {}
    approx_over_time = {}
    for iso_data in raw_values:
        that_date = datetime.fromisoformat(iso_data)
        gases_over_time[that_date] = raw_values[iso_data]['gas']
        if 'approx_gas' in raw_values[iso_data]:
            approx_over_time[that_date] = raw_values[iso_data]['approx_gas']
        else:
            approx_over_time[that_date] = {"NO2": 0.0, "CO": 0.0, "NH3": 0.0}

    fig, (ax1, ax2) = plt.subplots(2, 1, constrained_layout=True)
    ax1.set_xlabel("Time")
    plt.xticks(rotation=45)
    ax1.set_ylabel("sensor output in kOhm")
    ax1.set_title("Gas Sensor readings")

    times = [y for y in gases_over_time.keys()]

    l1, = ax1.plot(times, [x['oxidising'] for x in gases_over_time.values()], "g")
    l2, = ax1.plot(times, [x['reducing'] for x in gases_over_time.values()], "r")
    l3, = ax1.plot(times, [x['nh3'] for x in gases_over_time.values()], "b")

    ax1.legend([l1, l2, l3], [
        "reducing gasses",
        "oxidising gases",
        "ammonia"
    ], loc="center right")

    ax2.set_xlabel("Time")
    ax2.set_ylabel("Approximated ppm")
    ax2.set_title("Approximated Gas")
    l4, = ax2.plot(times, [x['NO2'] for x in approx_over_time.values()], "c")
    l5, = ax2.plot(times, [x['CO'] for x in approx_over_time.values()], "m")

    ax3 = ax2.twinx()
    l6, = ax3.plot(times, [x['NH3'] for x in approx_over_time.values()], "y")
    ax2.legend([l4, l5], ["NO2", "CO"], loc="lower left")
    ax3.legend([l6], ["NH3"], loc="upper right")

    if day_only:
        xformatter = mdates.DateFormatter('%H:%M')
        plt.gcf().axes[0].xaxis.set_major_formatter(xformatter)
        plt.gcf().axes[1].xaxis.set_major_formatter(xformatter)
    plt.savefig(output, dpi=dpi)


def plot_light(raw_values: dict, output="light.png", day_only=True, dpi=300):
    light_over_time = {}
    for iso_data in raw_values:
        that_date = datetime.fromisoformat(iso_data)
        light_over_time[that_date] = raw_values[iso_data]['light']

    fig, ax1 = plt.subplots()
    ax1.set_xlabel("Time")
    plt.xticks(rotation=45)
    ax1.set_ylabel("Lux")
    ax1.set_title("Light over Time")

    times = [y for y in light_over_time.keys()]

    l1, = ax1.plot(times, [x['lux'] for x in light_over_time.values()], color="y")
    l2, = ax1.plot(times, [x['ir'] for x in light_over_time.values()], color="r")
    ax1.legend([l1, l2], ["Light (Visible+IR)", "Infrared"])
    if day_only:
        xformatter = mdates.DateFormatter('%H:%M')
        plt.gcf().axes[0].xaxis.set_major_formatter(xformatter)
    plt.savefig(output, dpi=dpi)


def _calc_approx_gas(gas_readings: dict):
    from math import log10
    # stolen here: https://forums.pimoroni.com/t/pms5003-gas-measurement-with-an-enviro-on-a-raspberry/15868/5
    # oxidising, NO2: ppm = Rs / (6.5 * R0)
    NO2 = gas_readings['oxidising'] / 6.5 / 20000
    # R0 chosen to give value approx 0.01 in fresh air (detectable = 0.05 to 10)
    # reducing,CO: ppm = 10^((log10(Rs / 3.5 / R0)) / -0.845 )
    CO = 10 ** ((log10(gas_readings['reducing'] / 3.5 / 150000)) / -0.845)
    # R0 chosen to give value approx 2 in fresh air (detectable = 1 to 1000)
    # NH3: ppm = =10^((log10(Rs / 0.77 / R0)) / -0.5335 )
    NH3 = 10 ** ((log10(gas_readings['nh3'] / 0.77 / 570000)) / -0.5335)
    # R0 chosen to give value approx 2 in fresh air (detectable = 1 to 300)
    return {
        'NO2': NO2,
        'CO': CO,
        'NH3': NH3
    }


if __name__ == "__main__":
    file = "local_cache.db"
    if os.path.isfile(f"./{file}"):
        db_path = f"./{file}"
    elif os.path.isfile(f"../{file}"):
        db_path = f"../{file}"
    else:
        logger.warning("Visualize: cannot run Visualize:MAIN because 'local.db' cannot be found")
        exit(1)
    # local import, dont do this at home kids
    import local_database
    import sqlite3
    try:
        local_db = local_database.LocalCache(db_path)
    except sqlite3.OperationalError:
        logger.error("Found local database but couldnt load the sqlite file")
        exit(2)

    limit_date_display = True
    days = 2
    args = sys.argv
    if len(args) > 2 and args[1] == "days":  # argparse is a think
        try:
            days = int(args[2])
            days = days*2
            if days > 2:
                limit_date_display = False
        except ValueError:
            days = 2

    print(f"Querying database for all data from {datetime.today().isoformat()[:16]} till {(datetime.today()-timedelta(seconds=3600*24*int(days/2))).isoformat()[:16]}")
    raw_data = local_db.fetch_by_aoe_date(datetime.today(), 3600*24*days)  # last 24 hours
    # calculating the approximation of gas that is not written into the database
    for key in raw_data:
        raw_data[key]['approx_gas'] = _calc_approx_gas(raw_data[key]['gas'])
    plot_weather(raw_data, day_only=limit_date_display)
    plot_particles(raw_data, day_only=limit_date_display)
    plot_gas(raw_data, day_only=limit_date_display)
    plot_light(raw_data, day_only=limit_date_display)