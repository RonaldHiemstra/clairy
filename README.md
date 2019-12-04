# Clairy

Clairy is a smart device that can clean your room's air as well as measure indoor air quality levels, humidity and temperature.

Clairy is now [VITESY](https://vitesy.com/)

The development of this platform is inspired by the information provided by an article on [All Things Data Science](https://volderette.de/using-python-to-get-data-from-your-clairy-natural-air-purifier/) and the [demo code](https://github.com/volderette/clairy).
Check the article on [All Things Data Science](https://volderette.de/using-python-to-get-data-from-your-clairy-natural-air-purifier/) to find your personal user_id and the serial number of your Clairy.

## Installation

Copy the contents of `custom_components/clairy_sensor` folder to `<config_dir>custom_components/clairy_sensor/`.

## Configuration

Add the platform clairy_sensor to the `configuration.yaml` file.

```yaml
sensor:
  - platform: clairy_sensor
    serial: !secret clairy_serial
    user_id: !secret clairy_user_id
```
