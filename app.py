from flask import Flask, render_template_string, request, jsonify
from datetime import datetime, timezone, timedelta
import sys

# Use zoneinfo (Python 3.9+) or fallback to pytz if needed.
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from pytz import timezone as ZoneInfo

# ---------------------------
# Earth: no extra constants needed.

# ---------------------------
# Mars Constants
SOL_SECONDS = 24 * 3600 + 40 * 60   # 88,800 seconds per Martian sol.
MARS_HOURS_PER_DAY = 24             # 24 Mars hours per sol.
MARS_HOUR_LENGTH = SOL_SECONDS / 24 # 3,700 seconds per Mars hour.
MARS_YEAR_SOLS = 668                # Assumed number of sols per Martian year.
# Mars reference: Earth 2025-01-01 00:00:00 UTC maps to Mars "0/01 01:03:05" at longitude 0.
MARS_REF_OFFSET_SECONDS = 3885

# ---------------------------
# Phobos Constants
PHOBOS_SOL_SECONDS = 7 * 3600 + 39 * 60   # 27,540 seconds per Phobos day.
PHOBOS_HOURS_PER_DAY = 9                  # 9 hours per Phobos day.
PHOBOS_HOUR_LENGTH = PHOBOS_SOL_SECONDS / PHOBOS_HOURS_PER_DAY  # 3,060 seconds per hour.
PHOBOS_YEAR_DAYS = 1000                   # Arbitrary for calendar purposes.

# ---------------------------
# Saturn Constants
SATURN_SOL_SECONDS = 10 * 63 * 60   # 37,800 seconds per Saturn day.
SATURN_HOURS_PER_DAY = 10           # 10 Saturn hours per day.
SATURN_HOUR_LENGTH = SATURN_SOL_SECONDS / SATURN_HOURS_PER_DAY  # 3,780 seconds per Saturn hour.
SATURN_YEAR_DAYS = 1000             # Arbitrary for calendar purposes.

# ---------------------------
# Conversion functions for Mars

def convert_earth_to_mars_date(earth_date, earth_timezone, planetary_longitude):
    """
    Converts an Earth datetime to a Mars datetime.
    Now returns the date in the format "sol/year HH:MM:SS" instead of "year/sol".
    """
    earth_date_utc = earth_date.astimezone(timezone.utc)
    ref_earth = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    elapsed_seconds = (earth_date_utc - ref_earth).total_seconds() + MARS_REF_OFFSET_SECONDS
    sols_elapsed = elapsed_seconds / SOL_SECONDS
    timezone_offset_in_sols = (planetary_longitude / 15) / MARS_HOURS_PER_DAY
    adjusted_sols = sols_elapsed + timezone_offset_in_sols
    sols_passed = int(adjusted_sols)
    fractional_sol = adjusted_sols - sols_passed
    total_mars_seconds = fractional_sol * SOL_SECONDS
    mars_hour = int(total_mars_seconds // MARS_HOUR_LENGTH)
    remainder = total_mars_seconds % MARS_HOUR_LENGTH
    mars_minute = int(remainder // 60)
    mars_second = int(remainder % 60)
    martian_year = sols_passed // MARS_YEAR_SOLS
    sol_of_year = (sols_passed % MARS_YEAR_SOLS) + 1
    # New format: sol_of_year first, then martian_year
    return f"{sol_of_year:02d}/{martian_year} {mars_hour:02}:{mars_minute:02}:{mars_second:02}"

def convert_mars_to_earth_date(mars_year, sol_of_year, mars_time_str, planetary_longitude, earth_timezone):
    """
    Converts a Mars datetime (with time in "HH:MM:SS") to an Earth datetime.
    Expects input in "sol/year" format (i.e. sol_of_year is provided first).
    Returns an Earth date string "dd/mm/yyyy HH:MM:SS" in the selected timezone.
    """
    try:
        parts = mars_time_str.split(":")
        if len(parts) != 3:
            raise ValueError("Invalid Mars time format.")
        mars_hour = int(parts[0])
        mars_minute = int(parts[1])
        mars_second = int(parts[2])
    except Exception as e:
        return f"Error parsing Mars time: {e}"
    total_mars_seconds = mars_hour * MARS_HOUR_LENGTH + mars_minute * 60 + mars_second
    mars_time_fraction = total_mars_seconds / SOL_SECONDS
    # Note: since input is now "sol/year", the calling code should swap the values:
    mars_total_sols_adjusted = mars_year * MARS_YEAR_SOLS + (sol_of_year - 1) + mars_time_fraction
    timezone_offset_in_sols = (planetary_longitude / 15) / MARS_HOURS_PER_DAY
    reference_offset_fraction = MARS_REF_OFFSET_SECONDS / SOL_SECONDS
    sols_elapsed = mars_total_sols_adjusted - reference_offset_fraction - timezone_offset_in_sols
    elapsed_seconds = sols_elapsed * SOL_SECONDS
    ref_earth = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    earth_date_utc = ref_earth + timedelta(seconds=elapsed_seconds)
    earth_date_local = earth_date_utc.astimezone(ZoneInfo(earth_timezone))
    return earth_date_local.strftime("%d/%m/%Y %H:%M:%S")

# ---------------------------
# Conversion functions for Phobos

def convert_earth_to_phobos_date(earth_date, earth_timezone, planetary_longitude):
    """
    Converts an Earth datetime to a Phobos datetime.
    Now returns the date in the format "Phobos day/year HH:MM:SS".
    """
    earth_date_utc = earth_date.astimezone(timezone.utc)
    ref_earth = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    elapsed_seconds = (earth_date_utc - ref_earth).total_seconds()
    phobos_days_elapsed = elapsed_seconds / PHOBOS_SOL_SECONDS
    offset_fraction = (planetary_longitude / 40) / PHOBOS_HOURS_PER_DAY
    adjusted_days = phobos_days_elapsed + offset_fraction
    days_passed = int(adjusted_days)
    fractional_day = adjusted_days - days_passed
    total_phobos_seconds = fractional_day * PHOBOS_SOL_SECONDS
    phobos_hour = int(total_phobos_seconds // PHOBOS_HOUR_LENGTH)
    remainder = total_phobos_seconds % PHOBOS_HOUR_LENGTH
    phobos_minute = int(remainder // 60)
    phobos_second = int(remainder % 60)
    # Compute Phobos "year" and "day" based on PHOBOS_YEAR_DAYS
    phobos_year = days_passed // PHOBOS_YEAR_DAYS
    phobos_day = (days_passed % PHOBOS_YEAR_DAYS) + 1
    # New format: day first then year
    return f"Phobos {phobos_day:02d}/{phobos_year} {phobos_hour:02}:{phobos_minute:02}:{phobos_second:02}"

def convert_phobos_to_earth_date(phobos_year, phobos_day, phobos_time_str, planetary_longitude, earth_timezone):
    """
    Converts a Phobos datetime (with time in "HH:MM:SS") to an Earth datetime.
    Now expects input in "day/year" format (i.e. phobos_day is provided first).
    Returns Earth date string "dd/mm/yyyy HH:MM:SS" in the selected timezone.
    """
    try:
        parts = phobos_time_str.split(":")
        if len(parts) != 3:
            raise ValueError("Invalid Phobos time format.")
        phobos_hour = int(parts[0])
        phobos_minute = int(parts[1])
        phobos_second = int(parts[2])
    except Exception as e:
        return f"Error parsing Phobos time: {e}"
    total_phobos_seconds = phobos_hour * PHOBOS_HOUR_LENGTH + phobos_minute * 60 + phobos_second
    phobos_time_fraction = total_phobos_seconds / PHOBOS_SOL_SECONDS
    # Since we now expect "day/year", the calling code should provide phobos_day first
    phobos_total_days_adjusted = phobos_year * PHOBOS_YEAR_DAYS + (phobos_day - 1) + phobos_time_fraction
    offset_fraction = (planetary_longitude / 40) / PHOBOS_HOURS_PER_DAY
    days_elapsed = phobos_total_days_adjusted - offset_fraction
    elapsed_seconds = days_elapsed * PHOBOS_SOL_SECONDS
    ref_earth = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    earth_date_utc = ref_earth + timedelta(seconds=elapsed_seconds)
    earth_date_local = earth_date_utc.astimezone(ZoneInfo(earth_timezone))
    return earth_date_local.strftime("%d/%m/%Y %H:%M:%S")

# ---------------------------
# Conversion functions for Saturn

def convert_earth_to_saturn_date(earth_date, earth_timezone, planetary_longitude):
    """
    Converts an Earth datetime to a Saturn datetime.
    Now returns the date in the format "day/year HH:MM:SS" instead of "year/day".
    """
    earth_date_utc = earth_date.astimezone(timezone.utc)
    ref_earth = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    elapsed_seconds = (earth_date_utc - ref_earth).total_seconds()
    saturn_days_elapsed = elapsed_seconds / SATURN_SOL_SECONDS
    timezone_offset_in_sats = (planetary_longitude / 36) / SATURN_HOURS_PER_DAY
    adjusted_days = saturn_days_elapsed + timezone_offset_in_sats
    days_passed = int(adjusted_days)
    fractional_day = adjusted_days - days_passed
    total_saturn_seconds = fractional_day * SATURN_SOL_SECONDS
    saturn_hour = int(total_saturn_seconds // SATURN_HOUR_LENGTH)
    remainder = total_saturn_seconds % SATURN_HOUR_LENGTH
    saturn_minute = int(remainder // 60)
    saturn_second = int(remainder % 60)
    saturn_year = days_passed // SATURN_YEAR_DAYS
    day_of_year = (days_passed % SATURN_YEAR_DAYS) + 1
    # New format: day_of_year first, then saturn_year
    return f"{day_of_year:02d}/{saturn_year} {saturn_hour:02}:{saturn_minute:02}:{saturn_second:02}"

def convert_saturn_to_earth_date(saturn_year, saturn_day, saturn_time_str, planetary_longitude, earth_timezone):
    """
    Converts a Saturn datetime (with time in "HH:MM:SS") to an Earth datetime.
    Now expects input in "day/year" format (i.e. saturn_day is provided first).
    Returns Earth date string "dd/mm/yyyy HH:MM:SS" in the selected timezone.
    """
    try:
        parts = saturn_time_str.split(":")
        if len(parts) != 3:
            raise ValueError("Invalid Saturn time format.")
        saturn_hour = int(parts[0])
        saturn_minute = int(parts[1])
        saturn_second = int(parts[2])
    except Exception as e:
        return f"Error parsing Saturn time: {e}"
    total_saturn_seconds = saturn_hour * SATURN_HOUR_LENGTH + saturn_minute * 60 + saturn_second
    saturn_time_fraction = total_saturn_seconds / SATURN_SOL_SECONDS
    # Since input is now "day/year", the calling code should provide saturn_day first
    saturn_total_days_adjusted = saturn_year * SATURN_YEAR_DAYS + (saturn_day - 1) + saturn_time_fraction
    timezone_offset_in_sats = (planetary_longitude / 36) / SATURN_HOURS_PER_DAY
    days_elapsed = saturn_total_days_adjusted - timezone_offset_in_sats
    elapsed_seconds = days_elapsed * SATURN_SOL_SECONDS
    ref_earth = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    earth_date_utc = ref_earth + timedelta(seconds=elapsed_seconds)
    earth_date_local = earth_date_utc.astimezone(ZoneInfo(earth_timezone))
    return earth_date_local.strftime("%d/%m/%Y %H:%M:%S")

# ---------------------------
# Flask Application (UI and API)

app = Flask(__name__)

TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Planet Time Converter</title>
  <style>
    /* (CSS omitted for brevity) */
  </style>
  <script>
    function updatePlanetInfo() {
      // (JavaScript omitted for brevity)
    }
    window.onload = updatePlanetInfo;
  </script>
</head>
<body>
  <header>
    <h1>Planet Time Converter</h1>
    <p>Convert time between Earth, Mars, Phobos, and Saturn</p>
  </header>
  <form method="post">
    <!-- (Form fields remain as before, but you may want to update placeholders:
         e.g., for Mars: "sol/year" instead of "year/sol", for Phobos/Saturn: "day/year") -->
    <input type="submit" value="Convert">
  </form>
  
  {% if result %}
    <div class="result">
      <h2>Result:</h2>
      <p>{{ result }}</p>
    </div>
  {% endif %}
</body>
</html>
'''

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    from_planet = request.form.get("from_planet", "Earth")
    to_planet = request.form.get("to_planet", "Mars")
    date_str = request.form.get("date", "")
    time_str = request.form.get("time", "")
    
    from_earth_timezone = request.form.get("from_earth_timezone", "UTC")
    to_earth_timezone = request.form.get("to_earth_timezone", "UTC")
    from_planetary_longitude_str = request.form.get("from_planetary_longitude", "0")
    to_planetary_longitude_str = request.form.get("to_planetary_longitude", "0")
    
    try:
        from_planetary_longitude = float(from_planetary_longitude_str)
    except:
        from_planetary_longitude = 0.0
    try:
        to_planetary_longitude = float(to_planetary_longitude_str)
    except:
        to_planetary_longitude = 0.0
    
    if request.method == "POST":
        if from_planet == to_planet:
            if from_planet == "Earth":
                try:
                    earth_date = datetime.strptime(date_str + " " + time_str, "%d/%m/%Y %H:%M:%S")
                    earth_date = earth_date.replace(tzinfo=ZoneInfo(from_earth_timezone))
                except Exception as e:
                    result = f"Error parsing Earth date/time: {e}"
                else:
                    converted_date = earth_date.astimezone(ZoneInfo(to_earth_timezone))
                    result = converted_date.strftime("%d/%m/%Y %H:%M:%S")
            elif from_planet == "Mars":
                try:
                    parts = date_str.split("/")
                    if len(parts) != 2:
                        raise ValueError("Mars date must be in 'sol/year' format.")
                    # Note: swapped order now: first value is sol_of_year, second is martian_year.
                    sol_of_year = int(parts[0])
                    mars_year = int(parts[1])
                except Exception as e:
                    result = f"Error parsing Mars date: {e}"
                else:
                    intermediate = convert_mars_to_earth_date(mars_year, sol_of_year, time_str, from_planetary_longitude, "UTC")
                    try:
                        intermediate_date = datetime.strptime(intermediate, "%d/%m/%Y %H:%M:%S")
                        intermediate_date = intermediate_date.replace(tzinfo=ZoneInfo("UTC"))
                    except Exception as e:
                        result = f"Error converting Mars to Earth: {e}"
                    else:
                        result = convert_earth_to_mars_date(intermediate_date, "UTC", to_planetary_longitude)
            elif from_planet == "Phobos":
                try:
                    parts = date_str.split("/")
                    if len(parts) != 2:
                        raise ValueError("Phobos date must be in 'day/year' format.")
                    # First value is phobos_day, second is phobos_year.
                    phobos_day = int(parts[0])
                    phobos_year = int(parts[1])
                except Exception as e:
                    result = f"Error parsing Phobos date: {e}"
                else:
                    intermediate = convert_phobos_to_earth_date(phobos_year, phobos_day, time_str, from_planetary_longitude, "UTC")
                    try:
                        intermediate_date = datetime.strptime(intermediate, "%d/%m/%Y %H:%M:%S")
                        intermediate_date = intermediate_date.replace(tzinfo=ZoneInfo("UTC"))
                    except Exception as e:
                        result = f"Error converting Phobos to Earth: {e}"
                    else:
                        result = convert_earth_to_phobos_date(intermediate_date, "UTC", to_planetary_longitude)
            elif from_planet == "Saturn":
                try:
                    parts = date_str.split("/")
                    if len(parts) != 2:
                        raise ValueError("Saturn date must be in 'day/year' format.")
                    # First value is day_of_year, second is saturn_year.
                    saturn_day = int(parts[0])
                    saturn_year = int(parts[1])
                except Exception as e:
                    result = f"Error parsing Saturn date: {e}"
                else:
                    intermediate = convert_saturn_to_earth_date(saturn_year, saturn_day, time_str, from_planetary_longitude, "UTC")
                    try:
                        intermediate_date = datetime.strptime(intermediate, "%d/%m/%Y %H:%M:%S")
                        intermediate_date = intermediate_date.replace(tzinfo=ZoneInfo("UTC"))
                    except Exception as e:
                        result = f"Error converting Saturn to Earth: {e}"
                    else:
                        result = convert_earth_to_saturn_date(intermediate_date, "UTC", to_planetary_longitude)
        # (Other conversion branches between different planets would be updated similarly.)
        elif from_planet == "Earth" and to_planet == "Mars":
            try:
                earth_date = datetime.strptime(date_str + " " + time_str, "%d/%m/%Y %H:%M:%S")
                earth_date = earth_date.replace(tzinfo=ZoneInfo(from_earth_timezone))
            except Exception as e:
                result = f"Error parsing Earth date/time: {e}"
            else:
                result = convert_earth_to_mars_date(earth_date, from_earth_timezone, to_planetary_longitude)
        # ... (Additional branches for other conversions; update any Mars/Phobos/Saturn input parsing similarly)
        else:
            result = "Invalid conversion selection."
    
    return render_template_string(TEMPLATE,
                                  result=result,
                                  from_planet=from_planet,
                                  to_planet=to_planet,
                                  date=date_str,
                                  time=time_str,
                                  from_earth_timezone=from_earth_timezone,
                                  to_earth_timezone=to_earth_timezone,
                                  from_planetary_longitude=from_planetary_longitude_str,
                                  to_planetary_longitude=to_planetary_longitude_str)

# ---------------------------
# API Endpoint with similar changes

@app.route("/api/convert", methods=["POST"])
def convert_api():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    from_planet = data.get("from_planet", "Earth")
    to_planet = data.get("to_planet", "Mars")
    date_str = data.get("date", "")
    time_str = data.get("time", "")
    from_earth_timezone = data.get("from_earth_timezone", "UTC")
    to_earth_timezone = data.get("to_earth_timezone", "UTC")
    from_planetary_longitude_str = data.get("from_planetary_longitude", "0")
    to_planetary_longitude_str = data.get("to_planetary_longitude", "0")

    try:
        from_planetary_longitude = float(from_planetary_longitude_str)
    except:
        from_planetary_longitude = 0.0
    try:
        to_planetary_longitude = float(to_planetary_longitude_str)
    except:
        to_planetary_longitude = 0.0

    result = None

    if from_planet == to_planet:
        if from_planet == "Earth":
            try:
                earth_date = datetime.strptime(date_str + " " + time_str, "%d/%m/%Y %H:%M:%S")
                earth_date = earth_date.replace(tzinfo=ZoneInfo(from_earth_timezone))
            except Exception as e:
                result = f"Error parsing Earth date/time: {e}"
            else:
                converted_date = earth_date.astimezone(ZoneInfo(to_earth_timezone))
                result = converted_date.strftime("%d/%m/%Y %H:%M:%S")
        elif from_planet == "Mars":
            try:
                parts = date_str.split("/")
                if len(parts) != 2:
                    raise ValueError("Mars date must be in 'sol/year' format.")
                sol_of_year = int(parts[0])
                mars_year = int(parts[1])
            except Exception as e:
                result = f"Error parsing Mars date: {e}"
            else:
                intermediate = convert_mars_to_earth_date(mars_year, sol_of_year, time_str, from_planetary_longitude, "UTC")
                try:
                    intermediate_date = datetime.strptime(intermediate, "%d/%m/%Y %H:%M:%S")
                    intermediate_date = intermediate_date.replace(tzinfo=ZoneInfo("UTC"))
                except Exception as e:
                    result = f"Error converting Mars to Earth: {e}"
                else:
                    result = convert_earth_to_mars_date(intermediate_date, "UTC", to_planetary_longitude)
        elif from_planet == "Phobos":
            try:
                parts = date_str.split("/")
                if len(parts) != 2:
                    raise ValueError("Phobos date must be in 'day/year' format.")
                phobos_day = int(parts[0])
                phobos_year = int(parts[1])
            except Exception as e:
                result = f"Error parsing Phobos date: {e}"
            else:
                intermediate = convert_phobos_to_earth_date(phobos_year, phobos_day, time_str, from_planetary_longitude, "UTC")
                try:
                    intermediate_date = datetime.strptime(intermediate, "%d/%m/%Y %H:%M:%S")
                    intermediate_date = intermediate_date.replace(tzinfo=ZoneInfo("UTC"))
                except Exception as e:
                    result = f"Error converting Phobos to Earth: {e}"
                else:
                    result = convert_earth_to_phobos_date(intermediate_date, "UTC", to_planetary_longitude)
        elif from_planet == "Saturn":
            try:
                parts = date_str.split("/")
                if len(parts) != 2:
                    raise ValueError("Saturn date must be in 'day/year' format.")
                saturn_day = int(parts[0])
                saturn_year = int(parts[1])
            except Exception as e:
                result = f"Error parsing Saturn date: {e}"
            else:
                intermediate = convert_saturn_to_earth_date(saturn_year, saturn_day, time_str, from_planetary_longitude, "UTC")
                try:
                    intermediate_date = datetime.strptime(intermediate, "%d/%m/%Y %H:%M:%S")
                    intermediate_date = intermediate_date.replace(tzinfo=ZoneInfo("UTC"))
                except Exception as e:
                    result = f"Error converting Saturn to Earth: {e}"
                else:
                    result = convert_earth_to_saturn_date(intermediate_date, "UTC", to_planetary_longitude)
    # (Other conversion branches follow a similar pattern and should be updated similarly.)
    else:
        result = "Conversion not supported."

    return jsonify({"result": result})

if __name__ == "__main__":
    app.run(debug=True)
