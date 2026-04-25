# Weather CLI

A simple command-line tool to get current weather information for any city using the OpenWeatherMap API.

## Features

- Get current weather for any city worldwide
- Support for metric (Celsius) and imperial (Fahrenheit) units
- Clean, formatted output with emojis
- Error handling for invalid cities and network issues

## Installation

1. Clone or download this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

1. Get a free API key from [OpenWeatherMap](https://openweathermap.org/api)
2. Copy the example environment file:

```bash
cp .env.example .env
```

3. Edit `.env` and add your API key:

```env
WEATHER_API_KEY=your_actual_api_key_here
```

## Usage

Basic usage:

```bash
python main.py "New York"
```

With imperial units (Fahrenheit):

```bash
python main.py London --units imperial
```

Help message:

```bash
python main.py --help
```

### Example Output

```
🌤️  Weather in Beijing, CN
========================================
Temperature: 15.5°C
Feels like: 14.2°C
Weather: Clear Sky
Humidity: 45%
Wind: 3.1 m/s
Pressure: 1013 hPa
Visibility: 10000 m
```

## Project Structure

```
weather-cli/
├── main.py              # CLI entry point and argument parsing
├── utils.py             # API interaction and data parsing
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment configuration
└── README.md           # This file
```

## Dependencies

- `requests` - HTTP library for API calls
- `python-dotenv` - Environment variable management

## Error Handling

The tool handles common errors:
- Missing API key with helpful instructions
- Invalid city names
- Network connectivity issues
- API rate limits or errors

## License

MIT