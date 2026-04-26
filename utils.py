"""
Weather API utilities - current weather + 5-day forecast
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

# Load .env from the project root; fallback to .env.backup if .env doesn't exist
_base_dir = Path(__file__).resolve().parent
dotenv_path = _base_dir / '.env'
if not dotenv_path.exists():
    dotenv_path = _base_dir / '.env.backup'
load_dotenv(dotenv_path=dotenv_path, override=True)

# API configuration
API_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"
GEO_BASE_URL = "https://api.openweathermap.org/geo/1.0/direct"
API_KEY_ENV_VAR = "OPENWEATHER_API_KEY"

# Debug: show API key status at startup (masked)
_key_preview = os.getenv(API_KEY_ENV_VAR, "")
if _key_preview:
    print(f"[weather] Loaded API key from {dotenv_path.name}: {_key_preview[:4]}...{_key_preview[-4:]}")
else:
    print(f"[weather] No API key found in {dotenv_path.name}")

# ── Chinese → English city name mapping ──────────────────────────
CITY_NAME_MAP: Dict[str, str] = {
    # 中国主要城市
    "北京": "Beijing",
    "上海": "Shanghai",
    "广州": "Guangzhou",
    "深圳": "Shenzhen",
    "杭州": "Hangzhou",
    "成都": "Chengdu",
    "南京": "Nanjing",
    "武汉": "Wuhan",
    "天津": "Tianjin",
    "重庆": "Chongqing",
    "西安": "Xi'an",
    "苏州": "Suzhou",
    "长沙": "Changsha",
    "郑州": "Zhengzhou",
    "东莞": "Dongguan",
    "青岛": "Qingdao",
    "沈阳": "Shenyang",
    "宁波": "Ningbo",
    "昆明": "Kunming",
    "大连": "Dalian",
    "厦门": "Xiamen",
    "合肥": "Hefei",
    "佛山": "Foshan",
    "福州": "Fuzhou",
    "哈尔滨": "Harbin",
    "济南": "Jinan",
    "温州": "Wenzhou",
    "长春": "Changchun",
    "石家庄": "Shijiazhuang",
    "常州": "Changzhou",
    "泉州": "Quanzhou",
    "南宁": "Nanning",
    "贵阳": "Guiyang",
    "南昌": "Nanchang",
    "太原": "Taiyuan",
    "烟台": "Yantai",
    "嘉兴": "Jiaxing",
    "南通": "Nantong",
    "金华": "Jinhua",
    "珠海": "Zhuhai",
    "惠州": "Huizhou",
    "徐州": "Xuzhou",
    "海口": "Haikou",
    "乌鲁木齐": "Urumqi",
    "绍兴": "Shaoxing",
    "中山": "Zhongshan",
    "台州": "Taizhou",
    "兰州": "Lanzhou",
    "三亚": "Sanya",
    "呼和浩特": "Hohhot",
    "银川": "Yinchuan",
    "西宁": "Xining",
    "拉萨": "Lhasa",
    "保定": "Baoding",
    "邯郸": "Handan",
    "潍坊": "Weifang",
    "临沂": "Linyi",
    "洛阳": "Luoyang",
    "襄阳": "Xiangyang",
    "芜湖": "Wuhu",
    "赣州": "Ganzhou",
    # 国际城市
    "东京": "Tokyo",
    "大阪": "Osaka",
    "京都": "Kyoto",
    "首尔": "Seoul",
    "釜山": "Busan",
    "曼谷": "Bangkok",
    "新加坡": "Singapore",
    "吉隆坡": "Kuala Lumpur",
    "雅加达": "Jakarta",
    "马尼拉": "Manila",
    "河内": "Hanoi",
    "胡志明市": "Ho Chi Minh City",
    "新德里": "New Delhi",
    "孟买": "Mumbai",
    "迪拜": "Dubai",
    "伦敦": "London",
    "巴黎": "Paris",
    "柏林": "Berlin",
    "罗马": "Rome",
    "马德里": "Madrid",
    "莫斯科": "Moscow",
    "纽约": "New York",
    "洛杉矶": "Los Angeles",
    "芝加哥": "Chicago",
    "旧金山": "San Francisco",
    "波士顿": "Boston",
    "华盛顿": "Washington",
    "悉尼": "Sydney",
    "墨尔本": "Melbourne",
    "多伦多": "Toronto",
    "温哥华": "Vancouver",
    "开罗": "Cairo",
    "伊斯坦布尔": "Istanbul",
    "香港": "Hong Kong",
    "澳门": "Macau",
    "台北": "Taipei",
}

# ── English → Chinese city name mapping (generated from CITY_NAME_MAP) ──
EN_TO_CN: Dict[str, str] = {v: k for k, v in CITY_NAME_MAP.items() if v}

# ── In-memory cache ───────────────────────────────────────────────
_cache: Dict[str, Dict[str, Any]] = {}

CACHE_TTL_WEATHER = 600       # 10 minutes
CACHE_TTL_FORECAST = 1800     # 30 minutes


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and entry["expires"] > datetime.now().timestamp():
        return entry["data"]
    return None


def _cache_set(key: str, data: Any, ttl: int):
    _cache[key] = {"data": data, "expires": datetime.now().timestamp() + ttl}


def _cache_key(*parts: str) -> str:
    return ":".join(parts).lower()


def _lookup_cn_name(en_name: str) -> str:
    """Return Chinese city name if known, else original English."""
    return EN_TO_CN.get(en_name, en_name)


# ── English weather description -> Chinese translation -------------
WEATHER_DESC_CN: Dict[str, str] = {
    "clear sky": "晴",
    "few clouds": "少云",
    "scattered clouds": "多云",
    "broken clouds": "阴",
    "overcast clouds": "阴",
    "light rain": "小雨",
    "moderate rain": "中雨",
    "heavy intensity rain": "大雨",
    "very heavy rain": "暴雨",
    "extreme rain": "特大暴雨",
    "light intensity shower rain": "阵雨",
    "shower rain": "阵雨",
    "heavy intensity shower rain": "大阵雨",
    "ragged shower rain": "零星阵雨",
    "light rain and snow": "雨夹雪",
    "rain and snow": "雨夹雪",
    "light shower snow": "阵雪",
    "shower snow": "阵雪",
    "light snow": "小雪",
    "snow": "雪",
    "heavy snow": "大雪",
    "sleet": "雨夹雪",
    "light shower sleet": "小阵雨夹雪",
    "shower sleet": "阵雨夹雪",
    "thunderstorm": "雷暴",
    "thunderstorm with light rain": "雷阵雨",
    "thunderstorm with rain": "雷阵雨",
    "thunderstorm with heavy rain": "大雷阵雨",
    "ragged thunderstorm": "雷暴",
    "light intensity drizzle": "小毛毛雨",
    "drizzle": "毛毛雨",
    "heavy intensity drizzle": "大毛毛雨",
    "drizzle rain": "毛毛雨",
    "shower drizzle": "阵毛毛雨",
    "mist": "薄雾",
    "fog": "雾",
    "haze": "霾",
    "smoke": "烟尘",
    "dust": "扬尘",
    "sand": "沙尘",
    "tornado": "龙卷风",
    "squalls": "狂风",
    "volcanic ash": "火山灰",
    "sky is clear": "晴",
}


WEEKDAY_CN = {
    "Monday": "星期一",
    "Tuesday": "星期二",
    "Wednesday": "星期三",
    "Thursday": "星期四",
    "Friday": "星期五",
    "Saturday": "星期六",
    "Sunday": "星期日",
}


def _translate_desc(desc_en: str) -> str:
    """Translate English weather description to Chinese."""
    key = desc_en.strip().lower()
    return WEATHER_DESC_CN.get(key, desc_en)


def resolve_city_name(city: str) -> str:
    """
    Resolve a city name to its English form.
    Chinese names are looked up via CITY_NAME_MAP first,
    then fall back to the OpenWeatherMap Geocoding API.
    """
    # Not Chinese — return as-is
    if not any("一" <= ch <= "鿿" or "　" <= ch <= "〿" or
               "＀" <= ch <= "￯" for ch in city):
        return city

    # 1. Built-in mapping
    if city in CITY_NAME_MAP:
        return CITY_NAME_MAP[city]

    # 2. Geocoding API fallback
    api_key = load_api_key()
    try:
        resp = requests.get(
            GEO_BASE_URL,
            params={"q": city, "limit": 1, "appid": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if results:
            return results[0].get("name", city)
    except Exception:
        pass

    # Return original — let the weather API return the error
    return city


def load_api_key() -> str:
    """Load API key from environment variable"""
    api_key = os.getenv(API_KEY_ENV_VAR)

    if not api_key:
        # Retry loading .env (with fallback to .env.backup)
        _base_dir = Path(__file__).resolve().parent
        dotenv_path = _base_dir / '.env'
        if not dotenv_path.exists():
            dotenv_path = _base_dir / '.env.backup'
        if dotenv_path.exists():
            load_dotenv(dotenv_path=dotenv_path, override=True)
            api_key = os.getenv(API_KEY_ENV_VAR)

    if not api_key:
        _base_dir = Path(__file__).resolve().parent
        has_env = (_base_dir / '.env').exists()
        has_backup = (_base_dir / '.env.backup').exists()

        if not has_env and not has_backup:
            hint = (
                "\n  Neither .env nor .env.backup found."
                "\n  Run:  cp .env.example .env"
                "\n  Then edit .env and set your API key:"
                f"\n  {API_KEY_ENV_VAR}=your_api_key_here"
            )
        else:
            hint = (
                "\n  Found .env file(s) but the API key is missing or empty."
                f"\n  Make sure your .env or .env.backup contains:"
                f"\n  {API_KEY_ENV_VAR}=your_api_key_here"
            )
        raise Exception(
            f"{API_KEY_ENV_VAR} environment variable not set.{hint}\n"
            "Get a free API key at: https://openweathermap.org/api"
        )
    return api_key


def _check_api_response(data: dict, context: str = "API"):
    """Check OpenWeatherMap response for errors, with specific 401 handling."""
    cod = data.get("cod")
    if cod and str(cod) != "200":
        msg = data.get("message", "Unknown error")
        if str(cod) == "401":
            raise Exception(
                "Invalid API key (401).\n"
                "  Your OpenWeatherMap API key is invalid or has been disabled.\n"
                "  Check your .env or .env.backup and ensure the API key is correct.\n"
                "  Get a new key at: https://home.openweathermap.org/api_keys"
            )
        raise Exception(f"{context} error: {msg}")


def fetch_weather(city: str, units: str = "metric") -> Dict[str, Any]:
    """
    Fetch current weather for a city from OpenWeatherMap API

    Args:
        city: City name
        units: Temperature units - "metric" (Celsius) or "imperial" (Fahrenheit)

    Returns:
        Dictionary containing weather data

    Raises:
        Exception: If API request fails or city not found
    """
    api_key = load_api_key()
    resolved = resolve_city_name(city)

    cache_key = _cache_key(resolved, units, "weather")
    cached = _cache_get(cache_key)
    if cached:
        cached["_cached"] = True
        return cached

    params = {
        "q": resolved,
        "appid": api_key,
        "units": units,
    }

    try:
        response = requests.get(API_BASE_URL, params=params, timeout=10)
        data = response.json()

        # Check for API errors (e.g., city not found, invalid API key)
        _check_api_response(data)

        response.raise_for_status()
        result = parse_weather_data(data, units)
        _cache_set(cache_key, result, CACHE_TTL_WEATHER)
        return result

    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {e}")
    except ValueError as e:
        raise Exception(f"Invalid response from API: {e}")


def parse_weather_data(data: Dict[str, Any], units: str) -> Dict[str, Any]:
    """Parse API response into a structured format"""
    main = data.get("main", {})
    weather = data.get("weather", [{}])[0]
    wind = data.get("wind", {})
    sys_data = data.get("sys", {})

    # Determine units for display
    if units == "metric":
        temp_unit = "C"
        wind_unit = "m/s"
    elif units == "imperial":
        temp_unit = "F"
        wind_unit = "mph"
    else:
        temp_unit = "K"
        wind_unit = "m/s"

    return {
        "city": _lookup_cn_name(data.get("name", "Unknown")),
        "country": sys_data.get("country", "Unknown"),
        "temperature": round(main.get("temp", 0), 1),
        "feels_like": round(main.get("feels_like", 0), 1),
        "temp_unit": temp_unit,
        "description": _translate_desc(weather.get("description", "")),
        "icon": weather.get("icon", "01d"),
        "humidity": main.get("humidity", 0),
        "pressure": main.get("pressure", 0),
        "wind_speed": round(wind.get("speed", 0), 1),
        "wind_unit": wind_unit,
        "wind_direction": wind.get("deg", 0),
        "visibility": data.get("visibility"),
        "clouds": data.get("clouds", {}).get("all", 0),
        "sunrise": sys_data.get("sunrise"),
        "sunset": sys_data.get("sunset"),
        "timestamp": data.get("dt"),
    }


def get_weather_emoji(description: str) -> str:
    """Get appropriate emoji for weather description"""
    if not description:
        return "🌤️"

    description_lower = description.lower()

    if "thunder" in description_lower or "storm" in description_lower:
        return "⛈️"
    elif "drizzle" in description_lower:
        return "🌦️"
    elif "rain" in description_lower:
        return "🌧️"
    elif "snow" in description_lower or "ice" in description_lower or "sleet" in description_lower:
        return "❄️"
    elif "fog" in description_lower or "mist" in description_lower or "haze" in description_lower:
        return "🌫️"
    elif "clear" in description_lower:
        return "☀️"
    elif "cloud" in description_lower:
        return "☁️"
    elif "smoke" in description_lower or "dust" in description_lower or "sand" in description_lower:
        return "💨"
    elif "tornado" in description_lower or "squall" in description_lower:
        return "🌪️"
    else:
        return "🌤️"


def fetch_weather_by_coords(lat: float, lon: float, units: str = "metric") -> Dict[str, Any]:
    """
    Fetch current weather using geographic coordinates (browser geolocation).
    """
    api_key = load_api_key()
    cache_key = _cache_key(str(lat), str(lon), units, "weather")
    cached = _cache_get(cache_key)
    if cached:
        cached["_cached"] = True
        return cached

    params = {"lat": lat, "lon": lon, "appid": api_key, "units": units}
    try:
        resp = requests.get(API_BASE_URL, params=params, timeout=10)
        data = resp.json()
        _check_api_response(data)
        resp.raise_for_status()
        result = parse_weather_data(data, units)
        _cache_set(cache_key, result, CACHE_TTL_WEATHER)
        return result
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {e}")


def fetch_forecast_by_coords(lat: float, lon: float, units: str = "metric") -> List[Dict[str, Any]]:
    """Fetch 5-day forecast using geographic coordinates."""
    api_key = load_api_key()
    cache_key = _cache_key(str(lat), str(lon), units, "forecast")
    cached = _cache_get(cache_key)
    if cached:
        cached["_cached"] = True
        return cached

    try:
        resp = requests.get(
            FORECAST_BASE_URL,
            params={"lat": lat, "lon": lon, "appid": api_key, "units": units},
            timeout=10,
        )
        data = resp.json()
        _check_api_response(data, context="Forecast")
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error fetching forecast: {e}")

    tz_offset = data.get("city", {}).get("timezone", 0)
    result = _build_daily_forecasts(data.get("list", []), units, tz_offset)
    _cache_set(cache_key, result, CACHE_TTL_FORECAST)
    return result


def fetch_forecast(city: str, units: str = "metric") -> List[Dict[str, Any]]:
    """
    Fetch 5-day / 3-hour forecast for a city and return one representative
    entry per day (midday closest to 12:00) with daily high/low.

    Only shows days starting from *tomorrow* — today's remaining forecast
    slots are skipped so the forecast is always forward-looking.
    """
    api_key = load_api_key()
    resolved = resolve_city_name(city)

    cache_key = _cache_key(resolved, units, "forecast")
    cached = _cache_get(cache_key)
    if cached:
        return cached

    params = {"q": resolved, "appid": api_key, "units": units}

    try:
        resp = requests.get(FORECAST_BASE_URL, params=params, timeout=10)
        data = resp.json()

        _check_api_response(data, context="Forecast")

        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error fetching forecast: {e}")

    timezone_offset = data.get("city", {}).get("timezone", 0)
    result = _build_daily_forecasts(data.get("list", []), units, timezone_offset)
    _cache_set(cache_key, result, CACHE_TTL_FORECAST)
    return result


def _build_daily_forecasts(
    entries: List[Dict], units: str, tz_offset: int = 0
) -> List[Dict]:
    """
    Group 3-hour forecast entries by calendar day in the city's *local*
    timezone.  Entries whose local time has already passed are filtered
    out, so the forecast always shows future days.
    """
    if units == "metric":
        temp_unit = "C"
    elif units == "imperial":
        temp_unit = "F"
    else:
        temp_unit = "K"

    now_local = datetime.now(timezone.utc) + timedelta(seconds=tz_offset)

    days: Dict[str, Dict] = {}
    target_hour = 12  # prefer entries near midday

    for entry in entries:
        # Convert to local datetime
        local_dt = datetime.fromtimestamp(
            entry["dt"] + tz_offset, tz=timezone.utc
        )

        # Skip entries whose local time is already past
        if local_dt <= now_local:
            continue

        date_key = local_dt.strftime("%Y-%m-%d")
        hour = local_dt.hour

        main = entry.get("main", {})
        weather = entry.get("weather", [{}])[0]
        temp = main.get("temp", 0)
        icon = weather.get("icon", "01d")
        desc = _translate_desc(weather.get("description", ""))
        humidity = main.get("humidity", 0)

        if date_key not in days:
            days[date_key] = {
                "temp_high": temp,
                "temp_low": temp,
                "humidity_sum": 0,
                "humidity_count": 0,
                "icon": icon,
                "description": desc,
                "best_diff": abs(hour - target_hour),
            }
        else:
            d = days[date_key]
            if temp > d["temp_high"]:
                d["temp_high"] = temp
            if temp < d["temp_low"]:
                d["temp_low"] = temp
            diff = abs(hour - target_hour)
            if diff < d["best_diff"]:
                d["best_diff"] = diff
                d["icon"] = icon
                d["description"] = desc

        days[date_key]["humidity_sum"] += humidity
        days[date_key]["humidity_count"] += 1

    # Build sorted list (up to 5 days)
    sorted_dates = sorted(days.keys())[:5]
    result = []
    for date_key in sorted_dates:
        d = days[date_key]
        dt = datetime.strptime(date_key, "%Y-%m-%d")
        day_name = WEEKDAY_CN.get(dt.strftime("%A"), dt.strftime("%A"))

        result.append({
            "date": date_key,
            "day_name": day_name,
            "temp_high": round(d["temp_high"], 1),
            "temp_low": round(d["temp_low"], 1),
            "temp_unit": temp_unit,
            "icon": d["icon"],
            "description": d["description"],
            "humidity": round(d["humidity_sum"] / d["humidity_count"]),
        })

    return result