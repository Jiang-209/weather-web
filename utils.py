"""
Weather API utilities - current weather + 5-day forecast
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from difflib import get_close_matches
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv
from pypinyin import lazy_pinyin

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

# Debug flag and counter for raw API response logging
_DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
_debug_req_count = 0


def _log_raw_response(context: str, data):
    """Print raw API response type and preview (first 5 requests only)."""
    global _debug_req_count
    if not _DEBUG or _debug_req_count >= 5:
        _debug_req_count += 1  # still increment to avoid counting issues
        return
    _debug_req_count += 1
    print(f"[debug] [{context}] type={type(data).__name__}, preview={str(data)[:200]}")

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

# ── Local China district data (loaded at startup) ──────────────────
_data_path = Path(__file__).resolve().parent / "data" / "china_locations.json"
try:
    with open(_data_path, "r", encoding="utf-8") as _f:
        CHINA_LOCATIONS: List[Dict] = json.load(_f)
    print(f"[weather] Loaded {len(CHINA_LOCATIONS)} local China locations")
except Exception:
    CHINA_LOCATIONS = []

# Built lazily on first call to find_best_match()
_location_index: Dict[str, int] = {}
_location_pinyin_idx: Dict[str, int] = {}
_location_names: List[str] = []
_built = False


def _build_index():
    """Precompute name→idx and pinyin→idx for O(1) lookup."""
    global _built, _location_index, _location_pinyin_idx, _location_names
    if _built:
        return
    _location_index.clear()
    _location_pinyin_idx.clear()
    _location_names.clear()
    for i, loc in enumerate(CHINA_LOCATIONS):
        n = loc.get("name", "")
        _location_names.append(n)
        _location_index[n] = i
        # Also index the normalized (suffix-stripped) form
        n_norm = normalize_city_name(n)
        if n_norm != n:
            _location_index[n_norm] = i
        # Pinyin index
        py = "".join(lazy_pinyin(n))
        _location_pinyin_idx[py] = i
    _built = True

# ── In-memory cache ───────────────────────────────────────────────
import copy as _copy

_cache: Dict[str, Dict[str, Any]] = {}

CACHE_TTL_WEATHER = 600       # 10 minutes
CACHE_TTL_FORECAST = 1800     # 30 minutes


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and entry["expires"] > datetime.now().timestamp():
        data = entry["data"]
        _log_cache("HIT", key, data)
        # Return a deep copy so callers can mutate freely without
        # contaminating the cached value (avoids the "first OK,
        # second crash" pattern caused by _cached / sunrise_str /
        # sunset_str mutations leaking into the cache store).
        return _copy.deepcopy(data)
    _log_cache("MISS", key)
    return None


def _cache_set(key: str, data: Any, ttl: int):
    # Store a deep copy so later mutations of the original object
    # (e.g. in app.py route handlers) don't corrupt the cache entry.
    _cache[key] = {"data": _copy.deepcopy(data), "expires": datetime.now().timestamp() + ttl}
    _log_cache("SET", key, data)


def _cache_key(*parts: str) -> str:
    return ":".join(parts).lower()


_DEBUG_CACHE = os.getenv("FLASK_DEBUG", "0") == "1"
_cache_hit_count = 0


def _log_cache(event: str, key: str, data=None):
    global _cache_hit_count
    if not _DEBUG_CACHE:
        return
    _cache_hit_count += 1
    if data is not None:
        print(f"[cache] {event} key={key} type={type(data).__name__}")
    else:
        print(f"[cache] {event} key={key}")


# Purge any stale cache entries leftover from a previous module lifetime
# (e.g. gunicorn preload, hot-reload, or dev server restart).
_cache.clear()


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


# ── Pinyin & fuzzy matching helpers ───────────────────────────────

def normalize_input(text: str) -> str:
    """Strip spaces, lowercase, and remove administrative suffixes."""
    text = text.strip().lower()
    for suffix in ("市", "区", "县", "镇", "乡"):
        if text.endswith(suffix) and len(text) > 2:
            text = text[:-1]
            break
    return text


def to_pinyin(text: str) -> str:
    """Convert Chinese text to pinyin (no spaces)."""
    return "".join(lazy_pinyin(text))


def find_best_match(user_input: str):
    """
    Match user input against the local China locations database.
    Matches in priority order:
      1) Exact match on name
      2) Contains match (input is substring of name)
      3) Exact match after normalizing input (strip suffix)
      4) Exact pinyin match
      5) difflib fuzzy match (cutoff 0.6)

    Returns the matched location dict or None if no match found.
    """
    if not CHINA_LOCATIONS:
        return None

    _build_index()
    raw = user_input.strip()

    # ① Exact match
    idx = _location_index.get(raw)
    if idx is not None:
        return CHINA_LOCATIONS[idx]

    # ② Contains match (e.g. "朝阳" in "朝阳区")
    for i, name in enumerate(_location_names):
        if raw in name:
            return CHINA_LOCATIONS[i]

    # ③ Normalized match (strip suffix from input)
    norm = normalize_input(raw)
    if norm != raw:
        idx = _location_index.get(norm)
        if idx is not None:
            return CHINA_LOCATIONS[idx]

    # ④ Exact pinyin match
    input_py = to_pinyin(raw)  # e.g. "chaoyangqu" → "chaoyangqu"
    input_py_normalized = to_pinyin(norm)  # e.g. "chaoyang"
    idx = _location_pinyin_idx.get(input_py)
    if idx is None:
        idx = _location_pinyin_idx.get(input_py_normalized)
    if idx is not None:
        return CHINA_LOCATIONS[idx]

    # ⑤ difflib fuzzy match (try against raw names and pinyin)
    # Build candidate list: raw name + pinyin for each location
    candidates = []
    for name in _location_names:
        candidates.append(name)
    close = get_close_matches(raw, candidates, n=1, cutoff=0.6)
    if close:
        idx = _location_index.get(close[0])
        if idx is not None:
            return CHINA_LOCATIONS[idx]

    # Also try fuzzy against pinyin
    pinyin_candidates = list(_location_pinyin_idx.keys())
    close_py = get_close_matches(input_py, pinyin_candidates, n=1, cutoff=0.6)
    if close_py:
        idx = _location_pinyin_idx.get(close_py[0])
        if idx is not None:
            return CHINA_LOCATIONS[idx]

    return None


# ── Chinese name normalization & special-case corrections ────────

# Suffixes to strip for district-level matching
_CITY_SUFFIXES = ("市", "区", "县", "镇", "乡")

# Override wrong OpenWeatherMap mappings (e.g. 临淄 → Linz)
# Key = user input, Value = correct English city name for the weather API
SPECIAL_CASES: Dict[str, str] = {
    "临淄": "Zibo",
    "临淄区": "Zibo",
}


def _is_chinese(text: str) -> bool:
    """Return True if text contains CJK characters."""
    return any("一" <= ch <= "鿿" or
               "　" <= ch <= "〿" or
               "＀" <= ch <= "﻿" for ch in text)


def normalize_city_name(name: str) -> str:
    """Strip common administrative suffixes from a Chinese city name."""
    for suffix in _CITY_SUFFIXES:
        if name.endswith(suffix) and len(name) > 2:
            return name[:-1]
    return name


def _geo_lookup(city: str, api_key: str):
    """Call OpenWeatherMap Geocoding API and return (lat, lon, eng_name, cn_name)
    or None on failure."""
    try:
        resp = requests.get(
            GEO_BASE_URL,
            params={"q": city, "limit": 1, "appid": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if isinstance(results, list) and results:
            entry = results[0]
            if isinstance(entry, dict):
                lat = entry.get("lat")
                lon = entry.get("lon")
                eng_name = entry.get("name", "")
                # Prefer Chinese local_name if available
                local_names = entry.get("local_names", {}) or {}
                cn_name = local_names.get("zh", "") or ""
                return (lat, lon, eng_name, cn_name)
    except Exception:
        pass
    return None


def resolve_city_name(city: str) -> str:
    """
    Resolve a Chinese city name to its English form.
    Priority: SPECIAL_CASES > CITY_NAME_MAP > Geocoding API.
    """
    if not _is_chinese(city):
        return city

    # 0. Special-case correction (override wrong mappings)
    if city in SPECIAL_CASES:
        return SPECIAL_CASES[city]

    # Normalize: strip 市/区/县/镇/乡
    base = normalize_city_name(city)

    # 1. Built-in mapping (try normalized first, then original)
    if base in CITY_NAME_MAP:
        return CITY_NAME_MAP[base]
    if city in CITY_NAME_MAP:
        return CITY_NAME_MAP[city]

    # 2. Geocoding API fallback
    api_key = load_api_key()
    geo = _geo_lookup(city, api_key)
    if geo:
        return geo[2]  # eng_name

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


def _check_api_response(data, context: str = "API"):
    """Check OpenWeatherMap response for errors, with specific 401 handling.

    Validates that data is a dict before accessing fields, to avoid
    ``list indices must be integers or slices, not str`` when the API
    returns an unexpected format (e.g. list, gateway error page).
    """
    if not isinstance(data, dict):
        raise Exception(
            f"Unexpected API response format: expected a JSON object, "
            f"got {type(data).__name__}. "
            f"Raw preview: {str(data)[:200]}"
        )
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
    Fetch current weather from OpenWeatherMap.
    Priority: local China-locations match → Geocoding API → city-name query.
    Supports fuzzy pinyin input (e.g. "chaoyang", "linzi").
    """
    api_key = load_api_key()

    # ── 1. Local China-locations matching (district / pinyin / fuzzy) ──
    location = find_best_match(city)
    if location:
        result = fetch_weather_by_coords(location["lat"], location["lon"], units)
        result["city"] = location["name"]
        return result

    # ── 2. Chinese input: fallback to Geocoding API ──────────────────
    if _is_chinese(city):
        if city in SPECIAL_CASES:
            return _fetch_weather_by_name(SPECIAL_CASES[city], units, api_key)

        geo = _geo_lookup(normalize_city_name(city), api_key)
        if geo:
            lat, lon, _eng, cn_name = geo
            result = fetch_weather_by_coords(lat, lon, units)
            if cn_name:
                result["city"] = cn_name
            return result

        resolved = resolve_city_name(city)
    else:
        resolved = city

    return _fetch_weather_by_name(resolved, units, api_key)


def _fetch_weather_by_name(resolved: str, units: str, api_key: str) -> Dict[str, Any]:
    """Weather lookup by city name (fallback path)."""
    cache_key = _cache_key(resolved, units, "weather")
    cached = _cache_get(cache_key)
    if cached:
        if not isinstance(cached, dict):
            raise Exception(
                f"Cache contamination: expected dict for weather key "
                f"'{cache_key}', got {type(cached).__name__}"
            )
        return cached

    params = {"q": resolved, "appid": api_key, "units": units}
    try:
        resp = requests.get(API_BASE_URL, params=params, timeout=10)
        data = resp.json()
        _log_raw_response("weather", data)
        _check_api_response(data)
        resp.raise_for_status()
        result = parse_weather_data(data, units)
        _cache_set(cache_key, result, CACHE_TTL_WEATHER)
        return result
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {e}")
    except ValueError as e:
        raise Exception(f"Invalid response from API: {e}")


def parse_weather_data(data: Dict[str, Any], units: str) -> Dict[str, Any]:
    """Parse API response into a structured format"""
    if not isinstance(data, dict):
        raise Exception(f"Cannot parse weather data: expected dict, got {type(data).__name__}")

    main = data.get("main", {})
    if not isinstance(main, dict):
        main = {}

    weather_list = data.get("weather", [])
    if not isinstance(weather_list, list) or not weather_list:
        weather = {}
    else:
        weather = weather_list[0]
    if not isinstance(weather, dict):
        weather = {}

    wind = data.get("wind", {})
    if not isinstance(wind, dict):
        wind = {}

    sys_data = data.get("sys", {})
    if not isinstance(sys_data, dict):
        sys_data = {}

    clouds = data.get("clouds", {})
    if not isinstance(clouds, dict):
        clouds = {}

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

    # ── Convert UTC timestamps to local time using city timezone offset ──
    tz_offset = data.get("timezone", 0)  # seconds from UTC
    if isinstance(tz_offset, (int, float)) and tz_offset != 0:
        _to_local = lambda ts: (
            datetime.fromtimestamp(ts + tz_offset, tz=timezone.utc).strftime("%H:%M")
            if ts else "N/A"
        )
        sunrise_str = _to_local(sys_data.get("sunrise"))
        sunset_str = _to_local(sys_data.get("sunset"))
    else:
        sunrise_str = "N/A"
        sunset_str = "N/A"

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
        "clouds": clouds.get("all", 0),
        "sunrise": sys_data.get("sunrise"),
        "sunset": sys_data.get("sunset"),
        "sunrise_str": sunrise_str,
        "sunset_str": sunset_str,
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
        if not isinstance(cached, dict):
            raise Exception(
                f"Cache contamination: expected dict for weather key "
                f"'{cache_key}', got {type(cached).__name__}"
            )
        return cached

    params = {"lat": lat, "lon": lon, "appid": api_key, "units": units}
    try:
        resp = requests.get(API_BASE_URL, params=params, timeout=10)
        data = resp.json()
        _log_raw_response("weather", data)
        _check_api_response(data)
        resp.raise_for_status()
        result = parse_weather_data(data, units)
        _cache_set(cache_key, result, CACHE_TTL_WEATHER)
        return result
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {e}")
    except ValueError as e:
        raise Exception(f"Invalid response from weather API: {e}")


def fetch_forecast_by_coords(lat: float, lon: float, units: str = "metric") -> List[Dict[str, Any]]:
    """Fetch 5-day forecast using geographic coordinates."""
    api_key = load_api_key()
    cache_key = _cache_key(str(lat), str(lon), units, "forecast")
    cached = _cache_get(cache_key)
    if cached:
        if not isinstance(cached, list):
            raise Exception(
                f"Cache contamination: expected list for forecast key "
                f"'{cache_key}', got {type(cached).__name__}"
            )
        return cached

    try:
        resp = requests.get(
            FORECAST_BASE_URL,
            params={"lat": lat, "lon": lon, "appid": api_key, "units": units},
            timeout=10,
        )
        data = resp.json()
        _log_raw_response("forecast", data)
        _check_api_response(data, context="Forecast")
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error fetching forecast: {e}")
    except ValueError as e:
        raise Exception(f"Invalid response from forecast API: {e}")

    # Defensive parse: validate city / list fields before use
    city_info = data.get("city", {})
    tz_offset = city_info.get("timezone", 0) if isinstance(city_info, dict) else 0
    forecast_list = data.get("list", [])
    if not isinstance(forecast_list, list):
        forecast_list = []
    result = _build_daily_forecasts(forecast_list, units, tz_offset)
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
        if not isinstance(cached, list):
            raise Exception(
                f"Cache contamination: expected list for forecast key "
                f"'{cache_key}', got {type(cached).__name__}"
            )
        return cached

    params = {"q": resolved, "appid": api_key, "units": units}

    try:
        resp = requests.get(FORECAST_BASE_URL, params=params, timeout=10)
        data = resp.json()
        _log_raw_response("forecast", data)

        _check_api_response(data, context="Forecast")

        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error fetching forecast: {e}")
    except ValueError as e:
        raise Exception(f"Invalid response from forecast API: {e}")

    city_info = data.get("city", {})
    timezone_offset = city_info.get("timezone", 0) if isinstance(city_info, dict) else 0
    forecast_list = data.get("list", [])
    if not isinstance(forecast_list, list):
        forecast_list = []
    result = _build_daily_forecasts(forecast_list, units, timezone_offset)
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
        # Safeguard: skip non-dict entries (e.g. list with strings)
        if not isinstance(entry, dict):
            continue

        dt_val = entry.get("dt")
        if dt_val is None:
            continue

        # Convert to local datetime
        local_dt = datetime.fromtimestamp(
            dt_val + tz_offset, tz=timezone.utc
        )

        # Skip entries whose local time is already past
        if local_dt <= now_local:
            continue

        date_key = local_dt.strftime("%Y-%m-%d")
        hour = local_dt.hour

        main = entry.get("main", {})
        if not isinstance(main, dict):
            main = {}

        weather_list = entry.get("weather", [])
        if not isinstance(weather_list, list) or not weather_list:
            weather = {}
        else:
            weather = weather_list[0]
        if not isinstance(weather, dict):
            weather = {}

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