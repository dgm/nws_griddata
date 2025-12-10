# NWS Grid Data Integration

Custom Home Assistant integration that fetches NWS (National Weather Service) gridded weather data with automatic grid coordinate updates.

## Features

- Automatically fetches and updates NWS grid coordinates
- Monitors for grid coordinate changes (NWS updates these periodically)
- No manual intervention or restarts required when coordinates change
- Updates every 15 minutes
- Provides time-series data for wind speed, wind direction, and temperature

## Installation

### HACS (Recommended)

1. Add this repository as a custom repository in HACS:
   - Go to HACS → Integrations → ⋮ (menu) → Custom repositories
   - Add URL: `https://github.com/yourusername/home_assistant_nws_griddata`
   - Category: Integration
2. Click "Install" on the NWS Grid Data integration
3. Restart Home Assistant
4. Add configuration to your `configuration.yaml`

### Manual Installation

1. Copy the `custom_components/nws_griddata` directory to your Home Assistant `custom_components` folder:
   ```
   <config_dir>/custom_components/nws_griddata/
   ```

2. Restart Home Assistant
3. Add the following to your `configuration.yaml`:
   ```yaml
   sensor:
     - platform: nws_griddata
       latitude: YOUR_LATITUDE
       longitude: YOUR_LONGITUDE
   ```

3. Restart Home Assistant

## Configuration

| Parameter | Required | Description |
|-----------|----------|-------------|
| latitude | Yes | Latitude coordinate |
| longitude | Yes | Longitude coordinate |

## Sensor Data

The integration creates four sensors:

- **sensor.nws_wind_speed_{lat}_{lon}**
  - State: Number of data points
  - Attributes: `values` (full time-series), `uom` (unit of measure), `gridId`, `gridX`, `gridY`, `updateTime`

- **sensor.nws_wind_direction_{lat}_{lon}**
  - State: Number of data points
  - Attributes: `values` (full time-series), `uom` (unit of measure), `gridId`, `gridX`, `gridY`, `updateTime`

- **sensor.nws_temperature_{lat}_{lon}**
  - State: Number of data points
  - Attributes: `values` (full time-series), `uom` (unit of measure), `gridId`, `gridX`, `gridY`, `updateTime`

- **sensor.nws_wind_gust_{lat}_{lon}**
  - State: Number of data points
  - Attributes: `values` (full time-series), `uom` (unit of measure), `gridId`, `gridX`, `gridY`, `updateTime`

## How It Works

1. On first run, the integration calls `https://api.weather.gov/points/{lat},{lon}` to get grid coordinates
2. It then fetches weather data from `https://api.weather.gov/gridpoints/{gridId}/{gridX},{gridY}`
3. Every 15 minutes, it updates the data
4. If the API returns a 404 or detects changed grid coordinates, it automatically refetches the grid coordinates
5. No restart or manual intervention required

## Example

```yaml
sensor:
  - platform: nws_griddata
    latitude: 40.7128
    longitude: -74.0060
```

This will create four sensors with the latest NWS gridded weather data, each containing full time-series data in their attributes.
