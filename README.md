# AirWatcher

Small project providing a layer of abstraction to get a specific setup going and make the usage somewhat easy without dabbling to much with the fine details. 

## Functionality

* communicate with a set of sensors, usually mounted on the GPIO Ports of a raspberry pi
* providing a small flask server to enter data in a provided mariadb/mysql server
* a communication standard for said data

## Narrow use case

i wrote this specifically to run on a *Raspberry Pi Zero W* combined with the following sensors:

* Pimironi Enviro+
  * a DHT22 like weather sensor on BME280
  * a LTR559 Light Sensor
  * a gas sensor connected via i2c on ADS1015/ADS1115
  * a noise sensor (magically attached to the board)
* an attached PMS5003 particular matter sensor
* a jerry rigged CO2 sensor attached to the ports of the Enviro+

## More words

i must say that the library provided by Pimironi is somewhat weird, its serviceable but i would have done some things differently. Especially the usage of Numpy for one Fast Fourier Transformation seems a bit excessive, when testing, Numpy compiled for like an hour on my poor Pi Zero