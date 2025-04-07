from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from pytz import timezone as ZoneInfo

app = Flask(__name__)

# Index map
SOL_SECONDS_IDX = 0
HOURS_PER_DAY_IDX = 1
HOUR_LENGTH_IDX = 2
DAYS_PER_YEAR_IDX = 3
LONG_DIVISOR_IDX = 4
REF_OFFSET_IDX = 5

# Constants per planet
PLANET_CONSTANTS = {
    "Earth": {
        "constants": [86400, 24, 3600, 365, 15.0, 0],
        "reference": datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    },
    "Mars": {
        "constants": [88800, 24, 3700.0, 668, 15.0, 3885],
        "reference": datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    },
    "Phobos": {
        "constants": [27540, 9, 3060.0, 1000, 40.0, 0],
        "reference": datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    },
    "Saturn": {
        "constants": [37800, 10, 3780.0, 1000, 36.0, 0],
        "reference": datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    }
}

# -------------------------------
# Helper functions

def parse_earth_datetime(date_str, time_str, tz_str):
    dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
    return dt.replace(tzinfo=ZoneInfo(tz_str))

def format_earth_datetime(dt, tz_str):
    return dt.astimezone(ZoneInfo(tz_str)).strftime("%d/%m/%Y %H:%M:%S")

def convert_from_earth(earth_dt, planet_constants, longitude):
    sol_seconds, hours_per_day, hour_length, year_days, long_div, offset = planet_constants
    ref_dt = PLANET_CONSTANTS["Earth"]["reference"]
    elapsed = (earth_dt - ref_dt).total_seconds() + offset
    total_sols = elapsed / sol_seconds
    long_offset = (longitude / long_div) / hours_per_day
    adjusted = total_sols + long_offset
    day_count = int(adjusted)
    frac = adjusted - day_count
    total_sec = frac * sol_seconds
    hour = int(total_sec // hour_length)
    min = int((total_sec % hour_length) // 60)
    sec = int((total_sec % hour_length) % 60)
    year = day_count // year_days
    day = (day_count % year_days) + 1
    return f"{year}/{day:02d} {hour:02}:{min:02}:{sec:02}"

def convert_planet_to_earth_datetime(planet_dt_str, time_str, planet_constants, longitude):
    date_parts = planet_dt_str.split("/")
    year = int(date_parts[0])
    day = int(date_parts[1])
    hour, minute, second = map(int, time_str.split(":"))

    sol_seconds, hours_per_day, hour_length, year_days, long_div, offset = planet_constants
    time_sec = hour * hour_length + minute * 60 + second
    total_days = year * year_days + (day - 1) + (time_sec / sol_seconds)
    long_offset = (longitude / long_div) / hours_per_day
    adjusted_days = total_days - long_offset
    elapsed_sec = adjusted_days * sol_seconds - offset
    ref_dt = PLANET_CONSTANTS["Earth"]["reference"]
    return ref_dt + timedelta(seconds=elapsed_sec)

def convert_to_earth_string(planet_dt_str, time_str, planet_constants, longitude, tz):
    earth_dt = convert_planet_to_earth_datetime(planet_dt_str, time_str, planet_constants, longitude)
    return format_earth_datetime(earth_dt, tz)

# -------------------------------
# API route

@app.route("/api/convert", methods=["POST"])
def convert_api():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    from_planet = data.get("from_planet")
    to_planet = data.get("to_planet")
    date = data.get("date")
    time = data.get("time")
    from_tz = data.get("from_earth_timezone", "UTC")
    to_tz = data.get("to_earth_timezone", "UTC")
    from_long = float(data.get("from_planetary_longitude", 0))
    to_long = float(data.get("to_planetary_longitude", 0))

    if from_planet not in PLANET_CONSTANTS or to_planet not in PLANET_CONSTANTS:
        return jsonify({"error": "Unsupported planet"}), 400

    from_constants = PLANET_CONSTANTS[from_planet]["constants"]
    to_constants = PLANET_CONSTANTS[to_planet]["constants"]

    try:
        if from_planet == to_planet:
            if from_planet == "Earth":
                dt = parse_earth_datetime(date, time, from_tz)
                result = format_earth_datetime(dt, to_tz)
            else:
                earth_dt = convert_planet_to_earth_datetime(date, time, from_constants, from_long)
                result = convert_from_earth(earth_dt, to_constants, to_long)

        elif from_planet == "Earth":
            earth_dt = parse_earth_datetime(date, time, from_tz)
            result = convert_from_earth(earth_dt, to_constants, to_long)

        elif to_planet == "Earth":
            result = convert_to_earth_string(date, time, from_constants, from_long, to_tz)

        else:
            # FULL interplanetary: planet → Earth → planet
            earth_dt = convert_planet_to_earth_datetime(date, time, from_constants, from_long)
            result = convert_from_earth(earth_dt, to_constants, to_long)

    except Exception as e:
        result = f"Error during conversion: {e}"

    return jsonify({"result": result})

# -------------------------------
# Entry point

if __name__ == "__main__":
    app.run(debug=True)
