from flask import Flask, request, render_template_string
import requests

app = Flask(__name__)

API_URL = "https://planetarypi.onrender.com/api/convert"

PLANETS = ["Earth", "Mars", "Phobos", "Saturn"]
TIMEZONES = [
    "UTC", "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Moscow",
    "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
    "Asia/Tokyo", "Asia/Shanghai", "Asia/Dubai", "Asia/Kolkata",
    "Australia/Sydney", "Pacific/Auckland", "Africa/Johannesburg", "America/Sao_Paulo"
]

# Global result history (cleared on restart)
history_cache = []

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Planetary PI Direct Conversion</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 0;
      background-color: #fdf6f0;
    }
    header {
      background: linear-gradient(to right, #ff7e5f, #feb47b);
      color: white;
      padding: 20px;
      text-align: center;
    }
    .main {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      padding: 40px;
    }
    .form-box {
      background: linear-gradient(to right, #ff7e5f, #feb47b);
      padding: 30px;
      border-radius: 20px;
      width: 50%;
    }
    .result-box {
      width: 45%;
      background: #fff;
      padding: 30px;
      border-radius: 10px;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      font-size: 1.3em;
      font-weight: 600;
      color: #333;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
      border-left: 5px solid #ff7e5f;
    }
    .result-box p {
      margin-bottom: 20px;
      padding-bottom: 10px;
      border-bottom: 1px dashed #ddd;
    }
    label {
      display: block;
      margin-top: 15px;
      font-weight: bold;
    }
    input, select {
      width: 100%;
      padding: 8px;
      margin-top: 5px;
      border: 1px solid #ccc;
      border-radius: 8px;
    }
    .radio-group {
      display: flex;
      flex-wrap: wrap;
    }
    .radio-group label {
      margin-right: 10px;
    }
    button {
      background: #ff7e5f;
      color: white;
      border: none;
      padding: 12px 20px;
      border-radius: 10px;
      font-size: 16px;
      cursor: pointer;
      margin-top: 20px;
      width: 100%;
    }
  </style>
  <script>
    function updateFields() {
      const fromPlanet = document.querySelector('input[name="from_planet"]:checked').value;
      const toPlanet = document.querySelector('input[name="to_planet"]:checked').value;

      document.getElementById('from-tz-group').style.display = fromPlanet === 'Earth' ? 'block' : 'none';
      document.getElementById('from-long-group').style.display = fromPlanet !== 'Earth' ? 'block' : 'none';

      document.getElementById('to-tz-group').style.display = toPlanet === 'Earth' ? 'block' : 'none';
      document.getElementById('to-long-group').style.display = toPlanet !== 'Earth' ? 'block' : 'none';
    }

    window.onload = updateFields;
    document.addEventListener('DOMContentLoaded', () => {
      document.querySelectorAll('input[name="from_planet"]').forEach(r => r.addEventListener('change', updateFields));
      document.querySelectorAll('input[name="to_planet"]').forEach(r => r.addEventListener('change', updateFields));
    });
  </script>
</head>
<body>
<header>
  <h1>Planetary PI Direct Conversion</h1>
</header>
<div class="main">
  <div class="form-box">
    <form method="POST">
      <label>Convert From:</label>
      <div class="radio-group">
        {% for planet in planets %}
          <label><input type="radio" name="from_planet" value="{{ planet }}" {% if planet == from_planet %}checked{% endif %}> {{ planet }}</label>
        {% endfor %}
      </div>

      <div id="from-tz-group" style="display:none;">
        <label>Timezone:</label>
        <select name="from_tz">
          {% for tz in timezones %}
            <option value="{{ tz }}" {% if from_tz == tz %}selected{% endif %}>{{ tz }}</option>
          {% endfor %}
        </select>
      </div>

      <div id="from-long-group" style="display:none;">
        <label>Longitude:</label>
        <input type="number" name="from_long" step="0.01" value="{{ from_long }}">
      </div>

      <label>Convert To:</label>
      <div class="radio-group">
        {% for planet in planets %}
          <label><input type="radio" name="to_planet" value="{{ planet }}" {% if planet == to_planet %}checked{% endif %}> {{ planet }}</label>
        {% endfor %}
      </div>

      <div id="to-tz-group" style="display:none;">
        <label>Timezone:</label>
        <select name="to_tz">
          {% for tz in timezones %}
            <option value="{{ tz }}" {% if to_tz == tz %}selected{% endif %}>{{ tz }}</option>
          {% endfor %}
        </select>
      </div>

      <div id="to-long-group" style="display:none;">
        <label>Longitude:</label>
        <input type="number" name="to_long" step="0.01" value="{{ to_long }}">
      </div>

      <label>Date (dd/mm/yyyy or year/sol):</label>
      <input type="text" name="date">

      <label>Time (hh:mm:ss):</label>
      <input type="text" name="time">

      <button type="submit">Convert</button>
    </form>
  </div>
  <div class="result-box">
    {% if result_history %}
      {% for res in result_history %}
        <p>{{ res }}</p>
      {% endfor %}
    {% endif %}
  </div>
</div>
</body>
</html>
'''

@app.route("/", methods=["GET", "POST"])
def index():
    global history_cache
    from_planet = "Earth"
    to_planet = "Mars"
    from_tz = "UTC"
    to_tz = "UTC"
    from_long = 0
    to_long = 0

    if request.method == "POST":
        from_planet = request.form["from_planet"]
        to_planet = request.form["to_planet"]
        from_tz = request.form.get("from_tz", "UTC")
        to_tz = request.form.get("to_tz", "UTC")
        from_long = float(request.form.get("from_long", 0))
        to_long = float(request.form.get("to_long", 0))
        date = request.form.get("date", "")
        time = request.form.get("time", "")

        if date and time:
            payload = {
                "from_planet": from_planet,
                "to_planet": to_planet,
                "date": date,
                "time": time,
                "from_earth_timezone": from_tz if from_planet == "Earth" else "UTC",
                "to_earth_timezone": to_tz if to_planet == "Earth" else "UTC",
                "from_planetary_longitude": from_long if from_planet != "Earth" else 0,
                "to_planetary_longitude": to_long if to_planet != "Earth" else 0
            }

            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                data = response.json()
                from_loc = f"{from_long}°" if from_planet != "Earth" else from_tz
                to_loc = f"{to_long}°" if to_planet != "Earth" else to_tz
                result_str = f"{date} {time} on {from_planet} at {from_loc} is {data['result']} on {to_planet} at {to_loc}"
                history_cache.insert(0, result_str)
                history_cache = history_cache[:3]
            else:
                history_cache.insert(0, "Conversion failed.")
                history_cache = history_cache[:3]
        else:
            history_cache.insert(0, "Please enter both date and time.")
            history_cache = history_cache[:3]

    return render_template_string(HTML_TEMPLATE,
                                  planets=PLANETS,
                                  timezones=TIMEZONES,
                                  from_planet=from_planet,
                                  to_planet=to_planet,
                                  from_tz=from_tz,
                                  to_tz=to_tz,
                                  from_long=from_long,
                                  to_long=to_long,
                                  result_history=history_cache)

if __name__ == "__main__":
    app.run(debug=True)
