# Monoprice HTP-1 Integration for Unfolded Circle Remote

This integration provides complete control of Monoprice HTP-1 AV receivers for the Unfolded Circle Remote 2/3.

## Features

- Full media player control (power, volume, mute)
- Input source selection
- Sound mode (upmix) selection
- Real-time state updates via WebSocket
- Automatic reconnection on network disruption
- Built on ucapi-framework for reliability and performance

## Requirements

- Monoprice HTP-1 AV Receiver
- Network connectivity to the HTP-1
- Unfolded Circle Remote 2 or Remote 3

## Installation

### Via Remote Web Interface

1. Navigate to Integrations
2. Add new integration
3. Search for "Monoprice HTP-1"
4. Follow setup wizard

### Docker

```bash
docker run -d \
  --name uc-intg-monoprice-htp1 \
  --restart unless-stopped \
  --network host \
  -v ./config:/config \
  ghcr.io/mase1981/uc-intg-monoprice-htp1:latest
```

## Configuration

During setup, you will need to provide:
- **Device Name**: Friendly name for your HTP-1
- **IP Address**: Network IP address of your HTP-1

The integration connects to the HTP-1's built-in WebSocket interface at `ws://<ip>/ws/controller`.

## Supported Features

### Media Player Entity

- **Power Control**: Turn on/off
- **Volume Control**: Set volume, volume up/down
- **Mute Control**: Mute/unmute, toggle mute
- **Source Selection**: Select from visible inputs
- **Sound Mode**: Select upmix mode (DTS Neural:X, Dolby Surround, etc.)

### Remote Entity

- **Full UI Layout**: Pre-configured button layout for Remote UI
- **Power Control**: Toggle power
- **Volume Controls**: Volume up/down, mute
- **Navigation**: D-pad navigation (up, down, left, right, enter)
- **Menu Control**: Back, Home buttons
- **Activity Support**: All buttons available as simple commands for activities

### Sensor Entities

- **Input Sensor**: Currently selected input source
- **Volume Sensor**: Current volume level in dB
- **Sound Mode Sensor**: Active sound mode/upmix
- **Audio Format Sensor**: Detected audio codec and channels
- **Video Mode Sensor**: Current video resolution and HDR format
- **Connection Sensor**: Integration connection status

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/mase1981/uc-intg-monoprice-htp1.git
cd uc-intg-monoprice-htp1

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Locally

```bash
python -m intg_monoprice_htp1
```

### Debugging in VS Code

Open the project in VS Code and use the included launch configuration (F5).

## Testing

### Run Unit Tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all unit tests
python run_tests.py --unit

# Or use pytest directly
pytest -m "not integration"
```

### Run Integration Tests with Simulator

Integration tests use the included HTP-1 simulator:

```bash
# Start the simulator (in separate terminal)
python simulator/htp1_simulator.py --port 9999

# Run integration tests
python run_tests.py --integration
```

### Run All Tests with Coverage

```bash
python run_tests.py --coverage
```

Coverage report will be generated in `htmlcov/index.html`.

### Using the Simulator

The simulator can be used for manual testing without hardware:

```bash
# Start simulator on default port (80)
python simulator/htp1_simulator.py

# Or specify custom host/port
python simulator/htp1_simulator.py --host 127.0.0.1 --port 8080

# Enable debug logging
python simulator/htp1_simulator.py --debug
```

Then configure your integration to connect to the simulator's IP address and port.

See [simulator/README.md](simulator/README.md) for more details.

## Architecture

This integration is built using the ucapi-framework which provides:
- Automatic entity persistence and reboot survival
- Device lifecycle management
- WebSocket connection handling with automatic reconnection
- Event-driven state updates

### Key Components

- **device.py**: WebSocket device implementation with menu navigation support
- **media_player.py**: Media player entity with command handlers
- **remote.py**: Remote entity with full UI button layout
- **sensor.py**: Sensor entities for state monitoring
- **config.py**: Configuration data model
- **setup_flow.py**: Device setup and validation
- **driver.py**: Integration driver managing all entities

## License

MPL-2.0

## Author

Meir Miyara (meir.miyara@gmail.com)

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/mase1981/uc-intg-monoprice-htp1/issues).
