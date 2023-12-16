# homeassistant-metar
A sensor for METAR temperatures. https://en.wikipedia.org/wiki/METAR

## Configuration

To enable it, add the following lines to your `configuration.yaml`:

```yaml
# Example configuration.yaml entry
sensor:
  - platform: flying_weather
    route_name: "Luebeck-Hamburg"
    airport_codes:
      - EDHL
      - EDDH
    monitored_conditions:
      - time
      - flight_ruleset
```

### Configuration Variables

-  route_name

  (string)(Required) Your route name.

  -  airport_codes

    (List<string>)(Required) The *International Civil Aviation Organization*, *ICAO* codes for the airports on the route.

-  monitored_conditions

  (string)(Optional) What to read

It needs the metar python module.

It's a custom component so it must be downloaded under /custom_components folder.
