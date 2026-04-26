/**
 * Weather App - Frontend Logic
 * (auto-location, dynamic background, AJAX queries)
 */

(function () {
  "use strict";

  /* -------- DOM refs -------- */
  const form = document.getElementById("search-form");
  const cityInput = document.getElementById("city-input");
  const searchBtn = document.getElementById("search-btn");
  const loadingEl = document.getElementById("loading");
  const errorEl = document.getElementById("error");
  const weatherCard = document.getElementById("weather-card");
  const forecastSection = document.getElementById("forecast-section");
  const forecastGrid = document.getElementById("forecast-grid");
  const locateStatus = document.getElementById("locate-status");

  /* -------- State -------- */
  var isFetching = false;

  /* ================================================================
     HELPERS
     ================================================================ */

  function setLoading(on) {
    isFetching = on;
    searchBtn.disabled = on;
    loadingEl.classList.toggle("active", on);
  }

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.classList.add("active");
    weatherCard.classList.remove("active");
    forecastSection.classList.remove("active");
  }

  function hideError() {
    errorEl.classList.remove("active");
  }

  function iconUrl(icon) {
    return "https://openweathermap.org/img/wn/" + icon + "@2x.png";
  }

  function setLocateStatus(msg, active) {
    if (!locateStatus) return;
    locateStatus.textContent = msg || "";
    locateStatus.classList.toggle("active", active);
  }

  /* ================================================================
     DYNAMIC BACKGROUND (based on OpenWeatherMap icon code)
     ================================================================ */

  function setWeatherBackground(icon) {
    // Remove all bg-* classes
    var classes = document.body.className
      .split(/\s+/)
      .filter(function (c) { return c.indexOf("bg-") !== 0; });
    document.body.className = classes.join(" ");

    if (!icon) return;

    var code = icon.slice(0, 2);
    var isNight = icon.slice(-1) === "n";

    if (isNight && code === "01") {
      document.body.classList.add("bg-night");
    } else if (code === "01" || code === "02") {
      document.body.classList.add("bg-sunny");
    } else if (code === "03") {
      document.body.classList.add("bg-cloudy");
    } else if (code === "04") {
      document.body.classList.add("bg-overcast");
    } else if (code === "09" || code === "10") {
      document.body.classList.add("bg-rainy");
    } else if (code === "11") {
      document.body.classList.add("bg-storm");
    } else if (code === "13") {
      document.body.classList.add("bg-snow");
    } else if (code === "50") {
      document.body.classList.add("bg-fog");
    } else if (isNight) {
      document.body.classList.add("bg-night");
    } else {
      document.body.classList.add("bg-sunny");
    }
  }

  /* ================================================================
     RENDER
     ================================================================ */

  function renderWeather(data) {
    if (!data || !data.current) {
      showError("返回数据异常：缺少天气数据。");
      return;
    }
    var current = data.current;

    document.getElementById("w-city").textContent = current.city;
    document.getElementById("w-country").textContent = current.country;
    document.getElementById("w-temp").textContent =
      Math.round(current.temperature) + "°";
    document.getElementById("w-icon").src = iconUrl(current.icon);
    document.getElementById("w-icon").alt = current.description;
    document.getElementById("w-desc").textContent = current.description;
    document.getElementById("w-feels").textContent =
      Math.round(current.feels_like) + "°" + current.temp_unit;
    document.getElementById("w-humidity").textContent = current.humidity + "%";
    document.getElementById("w-wind").textContent =
      current.wind_speed + " " + current.wind_unit;
    document.getElementById("w-pressure").textContent = current.pressure + " hPa";
    document.getElementById("w-visibility").textContent =
      current.visibility
        ? (current.visibility / 1000).toFixed(1) + " km"
        : "N/A";
    document.getElementById("w-sunrise").textContent = current.sunrise_str;
    document.getElementById("w-sunset").textContent = current.sunset_str;

    weatherCard.classList.add("active");

    // Dynamic background
    setWeatherBackground(current.icon);
  }

  function renderForecast(list) {
    if (!list || !Array.isArray(list) || list.length === 0) {
      forecastSection.classList.remove("active");
      return;
    }

    forecastGrid.innerHTML = "";
    list.forEach(function (day) {
      var card = document.createElement("div");
      card.className = "forecast-card";

      card.innerHTML =
        '<div class="forecast-day">' +
        day.day_name +
        '</div>' +
        '<div class="forecast-date">' +
        day.date +
        '</div>' +
        '<img class="weather-icon" src="' +
        iconUrl(day.icon) +
        '" alt="' +
        day.description +
        '" loading="lazy">' +
        '<div class="forecast-temps"><span class="high">' +
        Math.round(day.temp_high) +
        "°</span><span class=\"low\">" +
        Math.round(day.temp_low) +
        "°</span></div>" +
        '<div class="forecast-desc">' +
        day.description +
        '</div>' +
        '<div class="forecast-humidity">💧 ' +
        day.humidity +
        "%</div>";

      forecastGrid.appendChild(card);
    });

    forecastSection.classList.add("active");
  }

  /* ================================================================
     API CALLS
     ================================================================ */

  function fetchWeatherCommon(formData, endpoint) {
    if (!endpoint) endpoint = "/api/weather";
    hideError();
    setLoading(true);

    fetch(endpoint, {
      method: "POST",
      body: formData,
    })
      .then(function (res) {
        if (!res.ok) {
          return res.json().then(function (err) {
            throw new Error(err.error || "请求失败");
          });
        }
        return res.json();
      })
      .then(function (json) {
        if (!json || typeof json !== "object") {
          showError("服务器返回异常数据格式。");
          return;
        }
        if (!json.success) {
          showError(json.error || "未知错误");
          return;
        }
        renderWeather(json);
        renderForecast(json.forecast);
      })
      .catch(function (err) {
        showError(err.message || "网络错误，请稍后重试。");
      })
      .finally(function () {
        setLoading(false);
        setLocateStatus("");
      });
  }

  function fetchWeather(city) {
    var fd = new FormData();
    fd.append("city", city);
    fd.append("units", "metric");
    fetchWeatherCommon(fd);
  }

  function fetchWeatherByCoords(lat, lon) {
    var fd = new FormData();
    fd.append("lat", lat);
    fd.append("lon", lon);
    fd.append("units", "metric");
    fetchWeatherCommon(fd, "/api/weather/coords");
  }

  /* ================================================================
     AUTO-LOCATION
     ================================================================ */

  function locateByGeolocation() {
    if (!navigator.geolocation) {
      setLocateStatus("");
      return;
    }

    setLocateStatus("正在定位…", true);

    navigator.geolocation.getCurrentPosition(
      function (pos) {
        setLocateStatus("已获取位置，正在查询天气…", true);
        fetchWeatherByCoords(pos.coords.latitude, pos.coords.longitude);
      },
      function () {
        // Geolocation denied / failed → IP fallback
        setLocateStatus("浏览器定位失败，尝试 IP 定位…", true);
        locateByIP();
      },
      { timeout: 8000, enableHighAccuracy: false }
    );
  }

  function locateByIP() {
    setLocateStatus("正在通过 IP 定位…", true);

    fetch("https://ip-api.com/json/?fields=city&lang=zh-CN")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        setLocateStatus("");
        if (data.city) {
          fetchWeather(data.city);
        } else {
          showError("无法自动定位，请手动输入城市名称。");
        }
      })
      .catch(function () {
        setLocateStatus("");
        showError("无法自动定位，请手动输入城市名称。");
      });
  }

  /* ================================================================
     EVENTS
     ================================================================ */

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var city = cityInput.value.trim();
    if (!city) {
      showError("请输入城市名称。");
      return;
    }
    setLocateStatus("");
    if (isFetching) return;
    fetchWeather(city);
  });

  /* ── Auto-locate on page load ── */
  document.addEventListener("DOMContentLoaded", function () {
    locateByGeolocation();
  });
})();
