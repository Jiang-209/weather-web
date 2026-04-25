"""Weather Web Application - Flask backend"""

import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from utils import (fetch_forecast, fetch_forecast_by_coords, fetch_weather,
                   fetch_weather_by_coords)

load_dotenv()

app = Flask(__name__)


def _format_timestamp(ts: int) -> str:
    """Convert UNIX timestamp to hour string."""
    return datetime.fromtimestamp(ts).strftime("%H:%M")


@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html")


@app.route("/api/weather", methods=["POST"])
def weather_api():
    """AJAX endpoint: return current weather + 5-day forecast as JSON."""
    city = request.form.get("city", "").strip()
    units = request.form.get("units", "metric")

    if not city:
        return jsonify(success=False, error="Please enter a city name."), 400

    try:
        current = fetch_weather(city, units)
        forecast_list = fetch_forecast(city, units)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 400

    # Format timestamps
    current["sunrise_str"] = _format_timestamp(current.get("sunrise", 0))
    current["sunset_str"] = _format_timestamp(current.get("sunset", 0))

    return jsonify(success=True, current=current, forecast=forecast_list)


@app.route("/api/weather/coords", methods=["POST"])
def weather_api_by_coords():
    """AJAX endpoint using lat/lon (from browser geolocation)."""
    try:
        lat = float(request.form.get("lat", ""))
        lon = float(request.form.get("lon", ""))
    except (ValueError, TypeError):
        return jsonify(success=False, error="Invalid coordinates."), 400

    units = request.form.get("units", "metric")

    try:
        current = fetch_weather_by_coords(lat, lon, units)
        forecast_list = fetch_forecast_by_coords(lat, lon, units)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 400

    current["sunrise_str"] = _format_timestamp(current.get("sunrise", 0))
    current["sunset_str"] = _format_timestamp(current.get("sunset", 0))

    return jsonify(success=True, current=current, forecast=forecast_list)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
