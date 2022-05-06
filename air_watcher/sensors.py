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

import time
import logging

from bme280 import BME280
from pms5003 import PMS5003, ReadTimeoutError
from enviroplus import gas
from enviroplus.noise import Noise  # TODO: erase that numpy requirement
# ? weather sensor
try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus
# ? light sensor
try:
    # Transitional fix for breaking change in LTR559
    from ltr559 import LTR559
    ltr559 = LTR559()
except ImportError:
    import ltr559

logger = logging.getLogger(__name__)


class SensorBundle:
    def __init__(self, demo=False):
        """
        If demo mode is True this will give dummy values for testing without the actual sensors
        :param demo:
        :type demo:
        """
        self.demo = False
        if not demo:
            self.particle = PMS5003()  # external particle matter sensor
            bus = SMBus(1)
            self.weather = BME280(i2c_dev=bus)  # basically dht22
            self.light = ltr559
            self.gas = gas
            self.noise = Noise()
        else:
            self.demo = True

    def get_all(self, one_shot=True):
        """
        An array with all values, apparently the sensors delive bullshit when used after
        a while so for a one_shot measurement a warm up cycle is initiated
        :return:
        :rtype:
        """
        if one_shot:
            self.warm_up_sensors()
        return {
            'gas': self.get_gas_readings(),
            'particles': self.get_particle_readings(),
            'weather': self.get_weather_readings(),
            'light': self.get_light_readings(),
            'noise': self.get_noise_readings()
        }

    def warm_up_sensors(self):
        """
        apparently the various sensors are doing nothing if left unattended and need
        some cycles till the measurements even out
        :return:
        :rtype:
        """
        if self.demo:
            return False
        for i in range(5):  # wind up
            self.gas.read_all()
            try:
                self.particle.read()
                self.weather.update_sensor()
                self.light.update_sensor()
            except ReadTimeoutError:
                self.particle = PMS5003()  # re initialize
        return True

    def get_gas_readings(self):
        """
        Returns the three available gas readings:

        * '`oxidising`' oxidising gases (Oxygen, hydrogen peroxide & halogens)
        * '`reducing`' reducing gasses (hydrogen, carbon monoxide)
        * '`nh3`' nh3 (ammonia)

        there is also an analog channel of questionable value
        :return:
        :rtype: dict
        """
        if self.demo:
            return {
                "oxidising": 13836.321122369447,
                "reducing": 748.0423767848918,
                "nh3": 381.21388936559697,
                "analog": None
            }  # actually measured in my apartment in germany at the 06.05.2022 13:28
        raw = self.gas.read_all()
        return {
            'oxidising': raw.oxidising,
            'reducing': raw.reducing,
            'nh3': raw.nh3,
            'analog': raw.adc
        }

    def get_particle_readings(self):
        """
        Returns a rather complex dictionary as particle size is divided in 1l and m³ measurements

        Particle reader needs some kind of windup
        :return:
        :rtype: dict
        """
        if self.demo:
            return {"m3": {
                        "atmo": {1.0: 4, 2.5: 6, 10: 6},
                        "non-atmo": {1.0: 4, 2.5: 6, 10: 6}
                        },
                    "1l": {0.3: 140, 0.5: 130, 1.0: 13, 2.5: 0, 5: 0, 10: 0}
            }  # apartment measurement 06.05.2022 14:39
        raw = self.particle.read()
        return {
            'm3': {
                'atmo': {
                    1.0: raw.pm_ug_per_m3(1.0, True),
                    2.5: raw.pm_ug_per_m3(2.5, True),
                    10: raw.pm_ug_per_m3(None, True),  # questionable
                },
                'non-atmo': {
                    1.0: raw.pm_ug_per_m3(1.0, False),
                    2.5: raw.pm_ug_per_m3(2.5, False),
                    10: raw.pm_ug_per_m3(10, False),
                }
            },
            '1l': {
                0.3: raw.pm_per_1l_air(0.3),
                0.5: raw.pm_per_1l_air(0.5),
                1.0: raw.pm_per_1l_air(1.0),
                2.5: raw.pm_per_1l_air(2.5),
                5: raw.pm_per_1l_air(5),
                10: raw.pm_per_1l_air(10),
            }
        }

    def get_weather_readings(self):
        """
        Gives us temperature, relative humidity and pressure. Those are correlated to each other and getting absolute
        humidity is a pain in the ass and not all that easy.

        Function named after DHT22, a common sensor for this
        :return:
        :rtype:
        """
        if self.demo:
            return {
              "temperature": 25.362881138194734,
              "pressure": 1010.8886041422448,
              "humidity": 33.79143792730413,
              "altitude": 19.67828936353579
            }  # my apartment 06.05.2022 14:56
        # qnh -> https://en.wikipedia.org/wiki/Pressure_altitude
        qnh = 1013.25
        self.weather.update_sensor()
        altitude = 44330.0 * (1.0 - pow(self.weather.pressure / qnh, (1.0 / 5.255)))
        # self.weather.get_altitude
        return {
            "temperature": self.weather.temperature,
            "pressure": self.weather.pressure,
            "humidity": self.weather.humidity,
            "altitude": altitude  # no clue how reliable this is
        }

    def get_light_readings(self):
        """
        Gives Light Readings

        TODO: add function to calibration behaviour
        :return:
        :rtype:
        """
        if self.demo:
            return {
                "lux": 292.17955,
                "proximity": 0,
                "ir": 373
           }
        self.light.update_sensor()
        return {
            'lux': self.light.get_lux(True),
            'proximity': self.light.get_proximity(True),
            'ir': self.light.get_raw_als(True)[1] # not entirely shore about this one
        }

    def get_noise_readings(self):
        """
        Gives some kind of noise reading?

        This is not so easy because it needs to be integrated over time
        :return:
        :rtype:
        """
        if self.demo:
            return {}
        return {
            '20-1K': self.noise.get_amplitude_at_frequency_range(20, 1000),
            '1K-3K': self.noise.get_amplitude_at_frequency_range(1000, 3000),
            '3K-8K': self.noise.get_amplitude_at_frequency_range(3000, 8000)
        }


# particle_reading = self.particle.read()
# temperature = self.weather.get_temperature()
# pressure = self.weather.get_pressure()
# humidity = self.weather.get_humidity()
# lux = ltr559.get_lux()
# prox = ltr559.get_proximity()
# readings = gas.read_all()