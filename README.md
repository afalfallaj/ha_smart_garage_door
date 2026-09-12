# Smart Garage Door - Home Assistant Custom Component

A Home Assistant custom component that creates smart garage door entities from binary sensors (open/closed) and toggle switches/lights. This integration automatically manages garage door states including "opening" detection and provides proper cover entities for control.

## Features

- **Multiple Garage Doors**: Add as many garage doors as needed
- **Smart State Detection**: Automatically detects open, closed, opening, and unavailable states
- **Template Sensors**: Creates intelligent sensors that track garage door state
- **Template Covers**: Provides proper garage door cover entities with open/close/stop functionality
- **Switch & Light Support**: Works with both switch and light entities (perfect for Shelly devices)
- **UI Configuration**: Setup, reconfiguration, and options all through Home Assistant's interface
- **Safety Logic**: Only allows operations when the garage door is in the correct state
- **HACS Compatible**: Easy installation through Home Assistant Community Store

## Installation

### HACS Installation (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL and select "Integration" as the category
6. Click "Add"
7. Search for "Smart Garage Door" and install it
8. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/smart_garage` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

> **Note**: `custom_components/smart_garage/brand/` ships icon/logo images built from the
> open-source `mdi:garage` glyph ([Material Design Icons](https://github.com/Pictogrammers/MaterialDesign),
> Apache 2.0 — see `brand/SOURCE.md`) so HACS/HA don't fall back to a generic icon. Swap them for
> dedicated artwork whenever you want a custom logo instead of the stock icon.

## Configuration

### UI Configuration (Recommended)

1. Go to **Settings** → **Devices & Services** → **Integrations**
2. Click **+ Add Integration**
3. Search for "Smart Garage Door"
4. Follow the setup wizard:
   - Enter a name for your garage door
   - Select your open sensor (binary_sensor)
   - Select your closed sensor (binary_sensor)
   - Select your toggle entity (switch or light)
   - Set the motion duration (default: 35 seconds)
5. Click **Submit**

Repeat this process for each garage door you want to add.

### Reconfiguring or tuning a garage door later

- **Wrong sensor/toggle entity, or renaming**: open the integration entry and choose
  **Reconfigure** to change the name, open sensor, closed sensor, or toggle entity without
  removing and re-adding the garage door.
- **Motion duration / sensor debounce**: open the integration entry and choose **Configure** to
  edit these as options at any time; the integration reloads automatically when you save.

### Configuration Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `name` | Yes | - | Friendly name for the garage door |
| `open_sensor` | Yes | - | Entity ID of the binary sensor that detects when the door is fully open |
| `closed_sensor` | Yes | - | Entity ID of the binary sensor that detects when the door is fully closed |
| `toggle_entity` | Yes | - | Entity ID of the switch or light that controls the garage door opener |
| `motion_duration` (option) | No | 35s | Time in seconds to consider the door as "opening" or "closing" after toggle |
| `sensor_debounce_ms` (option) | No | 300ms | How long to wait after a sensor changes before recomputing state, to smooth out sensor flicker |

> **Migrating from v1.x YAML configuration**: YAML setup (`smart_garage:` in
> `configuration.yaml`) was removed in v2.0.0 — it relied on a Home Assistant API removed in
> HA 2024.11, so it no longer worked anyway. Remove the `smart_garage:` block from your
> `configuration.yaml` and re-add each garage door through **Settings → Devices & Services →
> Add Integration** instead; your existing sensors/switch are unaffected.

### Supported Toggle Entities

The integration automatically detects the entity type and calls the appropriate service:

- **Switch entities** (`switch.*`): Calls `switch.toggle`
- **Light entities** (`light.*`): Calls `light.toggle`

This makes it perfect for Shelly devices that expose their relay outputs as light entities.

## Created Entities

For each configured garage door, the integration creates:

### Sensor Entities
- `sensor.smart_garage_[name]_state` - Shows the current state (open, closed, opening, unavailable)

### Cover Entities
- `cover.[name]` - Garage door cover entity with open/close/stop functionality

## State Logic

The integration uses the following logic to determine garage door states:

| Open Sensor | Closed Sensor | Previous State | Time Since Motion Start | State |
|-------------|---------------|----------------|-------------------------|-------|
| ON | ON | - | - | `unavailable` |
| ON | OFF | - | - | `open` |
| OFF | ON | - | - | `closed` |
| OFF | OFF | `open` | < motion_duration | `closing` |
| OFF | OFF | `closed` | < motion_duration | `opening` |
| OFF | OFF | - | ≥ motion_duration | `unavailable` |
| unavailable | - | - | - | `unavailable` |
| - | unavailable | - | - | `unavailable` |

### Smart Opening/Closing Detection

The integration follows a clear 6-step logic for state determination:

1. **Both sensors ON** → `unavailable` (impossible state)
2. **Open sensor ON** → `open` 
3. **Closed sensor ON** → `closed`
4. **Previous state was open + in motion** → `closing`
5. **Previous state was closed + in motion** → `opening`  
6. **Everything else** → `unavailable`

**Motion Detection**: Tracks when sensors transition from open/closed to both-off (motion start), allowing detection of any trigger method:
- ✅ **Manual operations**: Physical buttons, remotes, wall switches
- ✅ **Home Assistant cover commands**: Open, close, stop actions  
- ✅ **Other automations**: Any system that triggers the garage door
- ✅ **Fallback timing**: Uses toggle entity timing when motion start time isn't available

This ensures reliable state detection regardless of how the garage door is operated.

## Usage Examples

### Automation Examples

```yaml
# Notify when garage door is left open
automation:
  - alias: "Garage Door Left Open"
    trigger:
      - platform: state
        entity_id: cover.main_garage
        to: "open"
        for:
          minutes: 10
    action:
      - service: notify.mobile_app
        data:
          message: "Garage door has been open for 10 minutes"

# Auto-close garage door at night
automation:
  - alias: "Close Garage at Night"
    trigger:
      - platform: time
        at: "22:00:00"
    condition:
      - condition: state
        entity_id: cover.main_garage
        state: "open"
    action:
      - service: cover.close_cover
        target:
          entity_id: cover.main_garage
```

### Script Examples

```yaml
# Emergency stop all garage doors
script:
  emergency_stop_garages:
    alias: "Emergency Stop All Garages"
    sequence:
      - service: cover.stop_cover
        target:
          entity_id:
            - cover.main_garage
            - cover.side_garage
            - cover.basement_garage
```

### Dashboard Card Example

```yaml
type: entities
entities:
  - entity: cover.main_garage
    name: Main Garage Door
  - entity: sensor.smart_garage_main_garage_state
    name: Main Garage State
  - entity: cover.side_garage
    name: Side Garage Door (Shelly Light)
  - entity: sensor.smart_garage_side_garage_state
    name: Side Garage State
```

## Shelly Device Integration

This integration works perfectly with Shelly devices: when adding a garage door through the UI,
pick your Shelly door sensors as the open/closed sensors, and the Shelly relay's `light.*` entity
as the toggle entity.

## Safety Features

- **State Validation**: Cover operations only work when the garage door is in the appropriate state
- **Entity Type Detection**: Automatically uses the correct service for switch or light entities
- **Availability Checking**: Entities become unavailable if sensors are unavailable
- **UI Configuration**: User-friendly setup through Home Assistant interface
- **Logging**: Comprehensive logging for troubleshooting
- **Non-destructive**: Uses existing entities without modifying them

## Troubleshooting

### Enable Debug Logging

To troubleshoot issues (especially when covers show as "unavailable"), enable debug logging by adding this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.smart_garage: debug
```

After adding this, restart Home Assistant and check the logs at **Settings** → **System** → **Logs** or in your Home Assistant log file.

### Debug Log Analysis

When covers show as "unavailable", look for these key log messages (all from
`custom_components.smart_garage.garage`, since one tracker per garage door owns state derivation
for both its sensor and cover entities):

1. **Integration Setup**:
   ```
   Setting up Smart Garage from config entry: [Garage Name]
   ```

2. **Missing entities**:
   ```
   Garage '[Garage Name]': waiting on entities open=False closed=True toggle=True
   ```
   (`open=False` here means the open sensor entity itself doesn't exist yet/anymore)

3. **Motion tracking**:
   ```
   Motion started for '[Garage Name]': previous_state=open
   ```

4. **Failed transitions**:
   ```
   Garage '[Garage Name]' was opening but motion expired without reaching open state
   ```

### Common Issues

1. **Entities not created**: Verify entity IDs picked during setup still exist
   - Check logs for "waiting on entities open=... closed=... toggle=..."
   - Verify sensors exist in **Developer Tools** → **States**

2. **Cover/sensor show "unavailable"**: Usually means one of the tracked entities is missing or
   itself unavailable
   - Verify all three entities (open sensor, closed sensor, toggle) exist and report a real state
   - Use **Reconfigure** on the integration entry if you picked the wrong entity

3. **State stuck on "opening"/"closing"**: Check if the toggle entity ID is correct and state
   changes are detected
   - Look for "Motion started" / "motion expired" log lines
   - Increase `motion_duration` via the integration's **Configure** option if your door is slower
     than the current setting

4. **Toggle not working**: Verify the toggle entity domain (switch or light) is supported
   - Check logs for "Failed to call [domain].toggle for [entity]"
   - Ensure entity exists and is controllable

5. **UI configuration not available**: Restart Home Assistant after installation

### Debug Information to Collect

When reporting issues, please include:

1. **Configuration**: Your exact garage configuration (anonymize entity IDs if needed)
2. **Entity Status**: Check if your sensors and toggle entities exist in **Developer Tools** → **States**
3. **Debug Logs**: Relevant log entries with debug logging enabled
4. **Home Assistant Version**: Your HA version and when the issue started

## Requirements

- Home Assistant 2025.8.0 or newer
- Binary sensors for garage door open/closed detection
- Switch or light entity for garage door control


## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

*USE AT YOUR OWN RISK* This project is a personal hobby project provided for experimental purposes only. Its code is written and maintained with AI assistance rather than by hand line-by-line; it's reviewed before merging, but you should still read the source and test thoroughly in your own environment before controlling real heating/cooling hardware with it.

## Support

- Create an issue on GitHub for bugs or feature requests
- Check the Home Assistant Community forum for general questions
- Review the debug logs for troubleshooting information 