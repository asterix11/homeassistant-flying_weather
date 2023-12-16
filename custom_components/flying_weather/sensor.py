import logging, time
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from datetime import timedelta
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.const import ATTR_ATTRIBUTION, ATTR_TIME, CONF_MONITORED_CONDITIONS, TEMP_CELSIUS
try:
    from urllib2 import urlopen
except:
    from urllib.request import urlopen
from metar import Metar
import re

DOMAIN = 'flying_weather'
CONF_ROUTE_NAME = 'route_name'
CONF_AIRPORT_CODES = 'airport_codes'
SCAN_INTERVAL = timedelta(seconds=30)
BASE_URL = "https://tgftp.nws.noaa.gov/data/observations/metar/stations/"

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    'time': ['Updated', None],
    'flight_ruleset': ['Flight Ruleset', None],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_ROUTE_NAME): cv.string,
    vol.Required(CONF_AIRPORT_CODES, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_MONITORED_CONDITIONS, default=[]):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})

def setup_platform(hass, config, add_entities, discovery_info=None):
   route = {'route': str(config.get(CONF_ROUTE_NAME
)), 'codes': str(config.get(CONF_AIRPORT_CODES))}
   dev = []
   for variable in config[CONF_MONITORED_CONDITIONS]:
       dev.append(MetarSensor(route, variable, SENSOR_TYPES[variable][1]))
   add_entities(dev, True)


class MetarSensor(Entity):

    def __init__(self, route, sensor_type, temp_unit):
       self._state = None
       self._name = SENSOR_TYPES[sensor_type][0]
       self._unit_of_measurement = SENSOR_TYPES[sensor_type][1]
       self._route_name = route["route"]
       self._codes = route["codes"]
       self.type = sensor_type

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name + " " + self._route_name;

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    def update(self):
        """Get the latest data from Metar and updates the states."""

        states = []

        for code in self._codes:
            weather_data = MetarData({
                'code': code,
            })

            try:
                weather_data.update()
            except URLCallError:
                _LOGGER.error("Error when retrieving update data")
                return

            if weather_data is None:
                return

            qnh = 1013.25
            visibility = 9999
            clouds = []

            try:
                data = weather_data.sensor_data.press.string("")
                temp = data.split(" ")
                qnh = float(temp[0])
            except:
                _LOGGER.warning(
                    "QNH is currently not available!")

            try:
                data = weather_data.sensor_data.visibility()
                result = re.findall("([0-9]+)\\Wmeters", data)
                if len(result) == 1:
                    visibility = int(result[0])
            except:
                _LOGGER.warning(
                    "Visibility is currently not available!")
            try:
                data = weather_data.sensor_data.sky_conditions("\n     ")
                result = re.findall(".*(few|scattered|broken|overcast)[a-z\\W]+([0-9]+)\\Wfeet", data)
                result = sorted(list(map(lambda x : (1 if x[0] == 'overcast' else (2 if x[0] == 'broken' else (3 if x[0] == 'scattered' else (4 if x[0] == 'few' else -1))), int(x[1])), result)), key=lambda x : (x[1], x[0]))
                clouds = result
                _LOGGER.warning(data)
                _LOGGER.warning(clouds)
            except:
                _LOGGER.warning(
                    "Clouds are currently not available!")

            state = 0
            clouds_significant = list(filter(lambda x : (x[0] == 1 or x[0] == 2 or x[0] == 3) and x[1] <= 3000, clouds))
            if visibility > 8000 and len(clouds_significant) == 0:
                state = 3
            elif visibility > 5000 and clouds_significant[0][1] > 1000:
                state = 2
            elif visibility > 1500 and clouds_significant[0][1] > 500:
                state = 1

            states.push(state)

        try:
            if self.type == 'time':
                self._state = ""
            elif self.type == 'flight_ruleset':                
                result_state = int(floor(sum(states) / len(route["codes"])))
                
                self._state = "LIFR" if result_state == 0 else ("IFR" if result_state == 1 else ("MVFR" if result_state == 2 else "VFR"))
        except KeyError:
            self._state = None
            _LOGGER.warning(
                "Condition is currently not available: %s", self.type)

class MetarData:
    def __init__(self, airport):
       """Initialize the data object."""
       self._airport_code = airport["code"]
       self.sensor_data = None
       self.update()

    @Throttle(SCAN_INTERVAL)
    def update(self):
        url = BASE_URL + self._airport_code + ".TXT"
        try:
            urlh = urlopen(url)
            report = ''
            for line in urlh:
                if not isinstance(line, str):
                    line = line.decode() 
                if line.startswith(self._airport_code):
                    report = line.strip()
                    self.sensor_data = Metar.Metar(line)
                    _LOGGER.info("METAR ",self.sensor_data.string())
                    break
            if not report:
                _LOGGER.error("No data for ",self._airport_code,"\n\n")
        except Metar.ParserError as exc:
            _LOGGER.error("METAR code: ",line)
            _LOGGER.error(string.join(exc.args,", "),"\n")
        except:
            import traceback
            _LOGGER.error(traceback.format_exc())
            _LOGGER.error("Error retrieving",self._airport_code,"data","\n")