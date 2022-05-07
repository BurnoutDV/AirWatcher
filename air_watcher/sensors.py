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
import sounddevice
import wave
import numpy
from math import log10

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
    def __init__(self, demo=False, warmup_cycles=5):
        """
        If demo mode is True this will give dummy values for testing without the actual sensors
        :param demo:
        :type demo:
        """
        self.warmup_cycles = warmup_cycles
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

    def get_all(self, one_shot=True, condensed=False):
        """
        An array with all values, apparently the sensors delive bullshit when used after
        a while so for a one_shot measurement a warm up cycle is initiated
        :return:
        :rtype:
        """
        if one_shot:
            self.warm_up_sensors()
        raw_gas = self.get_gas_readings()
        return {
            'gas': raw_gas,
            'approx_gas': self.approx_gas_readings(raw_gas),
            'particles': self.get_particle_readings(reduced=condensed),
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
        for i in range(self.warmup_cycles):  # wind up
            self.gas.read_all()
            self.weather.update_sensor()
            self.light.update_sensor()
            try:
                self.particle.read()
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

    def approx_gas_readings(self, gas_readings=None):
        """
        The gas readings are wildly inaccurate and the sensor is definitely meant to be used as a qualitative tool,
        getting real ppm needs lab grade equipment which is rather expensive and needs finely calibrated equipment

        :param dict gas_readings: result of get_gas_readings()
        :return:
        """

        if not gas_readings:
            gas_readings = self.get_gas_readings()
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

    def get_particle_readings(self, reduced=False):
        """
        Returns a rather complex dictionary as particle size is divided in 1l and m³ measurements

        Pimoroni does not know what the difference between atmo and non-atmo is, i neither
        PM1.0 ug/m3 (ultrafine particles)
        PM2.5 ug/m3 (combustion particles, organic compounds, metals)
        PM10 ug/m3  (dust, pollen, mould spores)
        PM1.0 ug/m3 (atmos env)
        PM2.5 ug/m3 (atmos env)
        PM10 ug/m3 (atmos env)
        >0.3um in 0.1L air
        >0.5um in 0.1L air
        >1.0um in 0.1L air
        >2.5um in 0.1L air
        >5.0um in 0.1L air
        >10um in 0.1L air
        # bigger than x so that includes all of the above (0.3 includes 0.5 & 1.0)

        Particle reader needs some kind of windup
        :param bool reduced: most of the values are irrelevant, when true gives only 1.0, 2.5 and 10.0
        :return:
        :rtype: dict
        """
        if self.demo:
            if reduced:
                return {'m3': {'atmo': {1.0: 4, 2.5: 6, 10: 6}}}
            else:
                return {"m3": {
                            "atmo": {1.0: 4, 2.5: 6, 10: 6},
                            "non-atmo": {1.0: 4, 2.5: 6, 10: 6}
                            },
                        "1l": {0.3: 140, 0.5: 130, 1.0: 13, 2.5: 0, 5: 0, 10: 0}
                }  # apartment measurement 06.05.2022 14:39
        raw = self.particle.read()
        if reduced:
            return {
                'm3': {
                    'atmo': {
                        1.0: raw.pm_ug_per_m3(1.0, True),
                        2.5: raw.pm_ug_per_m3(2.5, True),
                        10: raw.pm_ug_per_m3(None, True),  # questionable
                    }
                }
            }
        else:
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
            'ir': self.light.get_raw_als(True)[1]  # not entirely shore about this one
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

    def record_audio(self, file_path: str, duration=10, sample_rate=16000, device='adau7002'):
        """
        this is probably a horrible idea and i only implemented it because we already got numpy in this project, apart
        from that i am really against using numpy for every little task but the example i copy & pasted this from used
        this. this also shows that the entire Noise() class does nothing specific as the whole magic is the device
        name

        :param str file_path:
        :param float duration: duration of the record, keep it short, script is unresponsive while recoding
        :param int sample_rate: sample rate of the recording, i am not sure but more than 16000 Hz might yield nothing
        :param str device: name of the device, i hope you know what you are doing, i do not
        :return: True if we get to the end, otherwise all the exception it can throw it will throw
        """
        data = sounddevice.rec(
            int(duration * sample_rate),
            device=device,
            samplerate=sample_rate,
            blocking=True,
            channels=1,
            dtype='float64'
        )
        sounddevice.wait()
        data = data / data.max() * numpy.iinfo(numpy.int16).max

        # float -> int
        data = data.astype(numpy.int16)

        # Save file
        with wave.open(file_path, mode='wb') as wb:
            wb.setnchannels(1)  # monaural
            wb.setsampwidth(2)  # 16bit=2byte
            wb.setframerate(sample_rate)
            wb.writeframes(data.tobytes())  # Convert to byte string
        return True

