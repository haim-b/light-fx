# Light FX for Home Assistant

WLED-like effects for any Home Assistant light entity.

## Features

- Create sequences of lights that work together
- Multiple effect types:
  - Rainbow wave
  - Color wipe
  - Twinkle
- Configurable effects:
  - Speed
  - Intensity
  - Color palettes
  - Direction (reverse)
  - Mirror mode
- Works with any light type:
  - WLED
  - Tasmota
  - Zigbee
  - ESPHome
  - Any HA light entity

## Installation

1. Add this repository to HACS:
   - HACS → Integrations → 3 dots menu → Custom repositories
   - Add URL: `https://github.com/yourusername/ha-addons`
   - Category: Integration

2. Install "Light FX" from HACS

3. Restart Home Assistant

## Configuration

Add to your `configuration.yaml`:

```yaml
light_fx:
  sequences:
    living_room:
      lights:
        - light.living_lamp1
        - light.living_lamp2
        - light.living_lamp3
      default_effect: rainbow
      default_speed: 50
      default_palette: rainbow
  update_frequency: 20  # Updates per second
  default_transition: 0.1  # Transition time in seconds
```

Or configure through the UI after adding the integration.

## Usage

### Services

#### light_fx.start_effect

Start an effect on a sequence of lights.

```yaml
service: light_fx.start_effect
data:
  sequence: living_room
  effect: rainbow
  config:
    speed: 50
    intensity: 100
    palette_name: rainbow
    reverse: false
    mirror: false
```

#### light_fx.stop_effect

Stop an effect on a sequence of lights.

```yaml
service: light_fx.stop_effect
data:
  sequence: living_room
```

## Available Effects

- `rainbow`: Flowing rainbow colors
- `color_wipe`: Colors wipe across the lights
- `twinkle`: Random twinkling lights

## Color Palettes

- `rainbow`: Full rainbow spectrum
- `fire`: Red to yellow gradient

## Example Automations

```yaml
automation:
  - alias: "Evening Light Show"
    trigger:
      platform: sun
      event: sunset
    action:
      service: light_fx.start_effect
      data:
        sequence: living_room
        effect: rainbow
        config:
          speed: 30
          intensity: 70
          palette_name: rainbow
```
