#!/usr/bin/env python3
"""
Weather CLI - Get current weather for a city
"""

import argparse
import io
import sys
from utils import fetch_weather, get_weather_emoji

# Fix console encoding on Windows (e.g., Chinese GBK can't handle ° and emoji)
if sys.stdout.encoding and sys.stdout.encoding.upper() not in ("UTF-8", "UTF8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser(
        description="Get current weather for a city"
    )
    parser.add_argument(
        "city",
        help="City name (e.g., 'Beijing', 'New York')"
    )
    parser.add_argument(
        "--units",
        choices=["metric", "imperial"],
        default="metric",
        help="Temperature units: metric (Celsius) or imperial (Fahrenheit). Default: metric"
    )

    args = parser.parse_args()

    try:
        weather_data = fetch_weather(args.city, args.units)
        display_weather(weather_data)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def display_weather(data):
    """Display weather information in a readable format"""
    emoji = get_weather_emoji(data.get("description", ""))
    print(f"\n{emoji}  Weather in {data['city']}, {data['country']}")
    print("=" * 40)
    print(f"Temperature: {data['temperature']}°{data['temp_unit']}")
    print(f"Feels like: {data['feels_like']}°{data['temp_unit']}")
    print(f"Weather: {data['description']}")
    print(f"Humidity: {data['humidity']}%")
    print(f"Wind: {data['wind_speed']} {data['wind_unit']}")
    print(f"Pressure: {data['pressure']} hPa")
    if 'visibility' in data:
        print(f"Visibility: {data['visibility']} m")
    print()


if __name__ == "__main__":
    main()