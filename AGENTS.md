# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based weather CLI (command-line interface) application that fetches current weather information for any city using the OpenWeatherMap API. The tool provides formatted output with temperature, humidity, wind speed, and other weather metrics.

## Common Development Tasks

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
# Basic usage
python main.py "New York"

# With imperial units
python main.py London --units imperial

# Show help
python main.py --help
```

### Setting Up Development Environment
```bash
# Copy environment template
cp .env.example .env
# Edit .env with your OpenWeatherMap API key
```

### Running Tests
*No tests are currently implemented. To add tests:*
```bash
# Install testing dependencies
pip install pytest requests-mock

# Run tests
pytest
```

## Architecture

### Key Components
1. **CLI Interface** (`main.py`): Uses argparse for command parsing, argument validation, and formatted output display
2. **Weather Service** (`utils.py`): Handles API communication with OpenWeatherMap, error handling, and data parsing
3. **Configuration Management**: Uses environment variables (`.env` file) for API key storage via python-dotenv
4. **Output Formatting**: Formats weather data with emojis and clean layout in the CLI output

### Project Structure
```
weather-cli/
├── main.py              # CLI entry point - argument parsing and display logic
├── utils.py             # Core weather API functions and data processing
├── requirements.txt     # Python dependencies (requests, python-dotenv)
├── .env.example         # Template for environment configuration
├── README.md           # User documentation and usage instructions
└── AGENTS.md           # Development guide for Codex
```

### Data Flow
1. User runs `python main.py "City Name" --units metric`
2. `main.py` parses arguments and calls `utils.fetch_weather(city, units)`
3. `utils.py` loads API key from environment, makes HTTP request to OpenWeatherMap
4. API response is parsed and formatted into a structured dictionary
5. `main.py` displays the formatted weather information to the user

## Configuration

### Environment Variables
- `WEATHER_API_KEY` (required): OpenWeatherMap API key. Get a free key at https://openweathermap.org/api
- `WEATHER_UNITS` (optional): Default temperature units - "metric" (Celsius) or "imperial" (Fahrenheit)

### Configuration Files
- `.env`: Contains environment variables (copy from `.env.example` and add your API key)
- No JSON/YAML config files - all configuration is via environment variables

### API Key Setup
1. Register for a free API key at OpenWeatherMap
2. Copy `.env.example` to `.env`: `cp .env.example .env`
3. Edit `.env` and replace `your_api_key_here` with your actual API key
4. The application automatically loads variables from `.env` on startup

## Development Notes

### API Integration
- Uses OpenWeatherMap Current Weather Data API (free tier available)
- API key is required and loaded from environment variables
- Implements proper error handling for HTTP errors, invalid responses, and missing data
- Supports both metric (Celsius) and imperial (Fahrenheit) units

### CLI Design
- Uses Python's built-in `argparse` module (no external CLI framework needed)
- Simple single-command interface: `python main.py "City Name" [--units metric|imperial]`
- Clear help text and error messages
- Formatted output with emojis for better readability

### Testing Strategy
- No tests currently implemented
- Recommended test approach:
  - Unit tests for `utils.parse_weather_data()` function
  - Mock API responses for `utils.fetch_weather()` tests
  - Integration tests with a test API key or mocked responses
  - Use `pytest` and `requests-mock` for testing

### Error Handling
- Missing API key: Clear instructions with link to get a key
- Invalid city: Shows API error message
- Network issues: Timeout after 10 seconds, informative error
- API limits: OpenWeatherMap free tier has 60 calls/minute limit

## Getting Started for New Developers

1. Install Python 3.7+ and pip
2. Clone the repository
3. Install dependencies: `pip install -r requirements.txt`
4. Get OpenWeatherMap API key: https://openweathermap.org/api
5. Copy `.env.example` to `.env` and add your API key
6. Run: `python main.py "London"`

## Notes for Future Codex Instances

- Project is now implemented with Python using OpenWeatherMap API
- Main entry point: `main.py`
- Core logic: `utils.py` (API calls, data parsing)
- Configuration: `.env` file with `WEATHER_API_KEY`
- Dependencies in `requirements.txt` (requests, python-dotenv)
- Update this AGENTS.md when adding new features or changing architecture