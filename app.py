from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import urllib.request
import json

app = Flask(__name__)
app.secret_key = 'multi_sport_fitness_ai_secret_key_2026'

# In-memory storage for users and activity history
users = {}
workout_logs = {}

def get_hyderabad_weather():
    url = "https://api.open-meteo.com/v1/forecast?latitude=17.3850&longitude=78.4867&current_weather=true"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'FitnessAI/1.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            res = json.loads(response.read().decode())
            curr = res.get('current_weather', {})
            temp = curr.get('temperature', 28.0)
            wind = curr.get('windspeed', 12.0)
            wcode = curr.get('weathercode', 0)
            
            if wcode in [0, 1]:
                condition = "Clear / Sunny"
            elif wcode in [2, 3]:
                condition = "Partly Cloudy"
            elif wcode >= 51:
                condition = "Rainy / Damp"
            else:
                condition = "Fair"

            return {
                "city": "Hyderabad",
                "temp": f"{temp}°C",
                "raw_temp": temp,
                "wind": f"{wind} km/h",
                "condition": condition,
                "status": "Live Data"
            }
    except Exception:
        return {
            "city": "Hyderabad",
            "temp": "28°C",
            "raw_temp": 28.0,
            "wind": "12 km/h",
            "condition": "Clear / Pleasant",
            "status": "Offline Preset"
        }

@app.route('/')
def index():
    return render_template('index.html', active_tab='login')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    user_hash = users.get(email)
    if user_hash and check_password_hash(user_hash, password):
        session['user'] = email
        return redirect(url_for('index'))
    return render_template('index.html', error="Invalid email or password.", active_tab='login')

@app.route('/register', methods=['POST'])
def register():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    if not email or not password:
        return render_template('index.html', error="Please enter both email and password.", active_tab='register')

    if email in users:
        return render_template('index.html', error="An account with this email already exists.", active_tab='register')

    users[email] = generate_password_hash(password)
    return render_template('index.html', success="Account created successfully! You can now log in.", active_tab='login')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/weather', methods=['GET'])
def weather_api():
    return jsonify(get_hyderabad_weather())

@app.route('/api/advisor', methods=['POST'])
def advisor():
    data = request.get_json() or {}
    sport = data.get('sport', 'cycling')
    duration = int(data.get('duration', 45))
    intensity = data.get('intensity', 'Moderate')
    fatigue = int(data.get('fatigue', 3))

    weather = get_hyderabad_weather()

    # Manual temperature override or auto live temperature
    custom_temp = data.get('custom_temp')
    if custom_temp is not None and str(custom_temp).strip() != '':
        try:
            temp_c = float(custom_temp)
            temp_mode = "Manual Override"
        except ValueError:
            temp_c = weather['raw_temp']
            temp_mode = weather['status']
    else:
        temp_c = weather['raw_temp']
        temp_mode = weather['status']

    weather_penalty = 8 if (temp_c > 32 and sport in ['cycling', 'running', 'hiit', 'team_sports']) else 0
    readiness_score = max(10, 100 - (fatigue * 9) - weather_penalty)

    if fatigue >= 7 or (intensity == "High" and duration > 60) or (temp_c > 35 and sport in ['cycling', 'running']):
        overexertion_risk = "High"
        risk_color = "#ef4444"
        hr_zones = [30, 40, 20, 10, 0]
    elif fatigue >= 4 or intensity == "High" or temp_c > 31:
        overexertion_risk = "Moderate"
        risk_color = "#f59e0b"
        hr_zones = [15, 30, 35, 15, 5]
    else:
        overexertion_risk = "Low"
        risk_color = "#10b981"
        hr_zones = [10, 20, 45, 20, 5]

    weather_insight = f"Thermal Load: {temp_c}°C ({temp_mode}). "
    if temp_c > 32 and sport in ['cycling', 'running', 'hiit']:
        weather_insight += "Heat alert active! Increase hydration and regulate pacing."
    elif temp_c < 20:
        weather_insight += "Cooler environment—extend warm-up to prevent connective tissue strains."
    else:
        weather_insight += "Optimal thermal window for outdoor workout."

    recommendations = {
        "cycling": {
            "title": "Outdoor / Indoor Cycling Advisory",
            "stat_label": "Target Cadence",
            "stat_val": "85 - 95 RPM",
            "hr_zone": "Zone 2-3 (Endurance)" if fatigue <= 5 else "Zone 1 (Active Recovery)",
            "ai_insight": f"Planned {duration}-min ride at {intensity.lower()} intensity with fatigue at {fatigue}/10. {weather_insight}",
            "nutrition_tip": "Hydrate every 15 mins. Consume 30-60g fast carbs per hour for sessions over 45 mins."
        },
        "running": {
            "title": "Running Telemetry Advisory",
            "stat_label": "Target Cadence",
            "stat_val": "165 - 175 SPM",
            "hr_zone": "Zone 2 (Base Aerobic)" if fatigue <= 4 else "Zone 1 (Flush Run)",
            "ai_insight": f"{duration}-min run planned at {intensity.lower()} effort. {weather_insight}",
            "nutrition_tip": "Prioritize rapid hydration and sodium balance to prevent muscle cramping."
        },
        "strength": {
            "title": "Strength & Resistance Advisory",
            "stat_label": "Target Focus",
            "stat_val": "Progressive Overload" if fatigue <= 4 else "Form Control & Deload",
            "hr_zone": "Rest Intervals: 90-180s",
            "ai_insight": f"Planned {duration}-min resistance session. Overexertion risk is {overexertion_risk.lower()}. Focus on controlled eccentrics.",
            "nutrition_tip": "Ingest 25-30g post-workout protein within 45 minutes for optimal muscle synthesis."
        },
        "hiit": {
            "title": "HIIT & Cardio Advisory",
            "stat_label": "Interval Ratio",
            "stat_val": "30s Work / 30s Rest" if fatigue <= 4 else "20s Work / 40s Rest",
            "hr_zone": "85% Max HR Cap" if fatigue <= 5 else "70% Max HR Guard",
            "ai_insight": f"{duration}-min high-intensity cardio protocol. {weather_insight}",
            "nutrition_tip": "Replenish essential electrolytes and fluid balance immediately post-workout."
        },
        "calisthenics": {
            "title": "Calisthenics & Bodyweight Advisory",
            "stat_label": "Volume Cap",
            "stat_val": "Sub-maximal Sets",
            "hr_zone": "Rest Intervals: 60-90s",
            "ai_insight": f"{duration}-min bodyweight skill & strength protocol. Protect shoulder girdle and wrist joints.",
            "nutrition_tip": "Maintain hydration and track intra-set neural fatigue."
        },
        "swimming": {
            "title": "Swimming & Aquatics Advisory",
            "stat_label": "Pace Target",
            "stat_val": "Aerobic Glide Pace",
            "hr_zone": "Zone 2 (Cardiovascular)",
            "ai_insight": f"{duration}-min swim session. Low joint impact environment reduces structural load.",
            "nutrition_tip": "Post-swim hydration is vital due to unrecognized perspiration in pool environments."
        },
        "combat": {
            "title": "Combat Sports & Martial Arts Advisory",
            "stat_label": "Round Structure",
            "stat_val": "Controlled Technical Rounds",
            "hr_zone": "Zone 3-4 (Anaerobic / Reactive)",
            "ai_insight": f"{duration}-min combat session. High neural demand. Pace explosive combinations carefully.",
            "nutrition_tip": "Consume simple carbohydrates intra-workout for fast neural firing."
        },
        "team_sports": {
            "title": "Team & Field Sports Advisory",
            "stat_label": "Sprint Management",
            "stat_val": "Regulated High-Speed Distance",
            "hr_zone": "Intermittent Zone 3-5",
            "ai_insight": f"{duration}-min field session. High deceleration and change-of-direction load on lower limbs.",
            "nutrition_tip": "High sodium replenishment required for dynamic multi-directional movements."
        },
        "yoga": {
            "title": "Yoga, Mobility & Pilates Advisory",
            "stat_label": "Focus Area",
            "stat_val": "Flow & Joint Range",
            "hr_zone": "Zone 1 (Parasympathetic)",
            "ai_insight": f"{duration}-min restorative practice. Excellent for nervous system recovery and fascia release.",
            "nutrition_tip": "Focus on warm herbal tea hydration and magnesium-dense nutrition."
        }
    }

    advice_data = recommendations.get(sport, recommendations["cycling"])

    return jsonify({
        "readiness_score": f"{readiness_score}%",
        "overexertion_risk": overexertion_risk,
        "risk_color": risk_color,
        "advice": advice_data,
        "weather": weather,
        "effective_temp": temp_c,
        "temp_mode": temp_mode,
        "hr_zones": hr_zones
    })

@app.route('/api/recovery', methods=['POST'])
def recovery_advisor():
    data = request.get_json() or {}
    sleep_hours = float(data.get('sleep_hours', 7.5))
    sleep_quality = data.get('sleep_quality', 'Good')
    soreness = int(data.get('soreness', 4))
    cns_strain = int(data.get('cns_strain', 3))

    sleep_score = min(100, int((sleep_hours / 8.0) * 80 + (20 if sleep_quality in ['Good', 'Excellent'] else 5)))
    recovery_index = max(10, int(sleep_score - (soreness * 4) - (cns_strain * 5)))

    if recovery_index >= 75:
        status = "Optimal Recovery"
        status_color = "#10b981"
        protocol = "Full training clearance. High CNS readiness for heavy resistance or intense speed work."
        actions = ["Dynamic mobility warm-up", "Standard hydration protocol", "Optimal neural firing ready"]
    elif recovery_index >= 50:
        status = "Moderate Fatigue"
        status_color = "#f59e0b"
        protocol = "Moderate clearance. Limit peak effort sets and prioritize active flushing."
        actions = ["15-min foam rolling session", "Contrast shower or cold water exposure", "Hydrate with 400mg Magnesium"]
    else:
        status = "High CNS Strain / Deload Recommended"
        status_color = "#ef4444"
        protocol = "Rest or low-intensity active recovery recommended to avoid overtraining."
        actions = ["Zone 1 walk or gentle restorative yoga", "Deep sleep focus (8.5+ hours)", "Cold therapy & soft tissue release"]

    return jsonify({
        "recovery_index": f"{recovery_index}%",
        "status": status,
        "status_color": status_color,
        "protocol": protocol,
        "actions": actions
    })

@app.route('/api/logs', methods=['GET', 'POST'])
def logs():
    user = session.get('user')
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    if user not in workout_logs:
        workout_logs[user] = []

    if request.method == 'POST':
        data = request.get_json() or {}
        new_entry = {
            "id": len(workout_logs[user]) + 1,
            "date": datetime.now().strftime("%d %b %Y, %H:%M"),
            "sport": data.get("sport", "General").capitalize(),
            "duration": f"{data.get('duration', 45)} mins",
            "intensity": data.get("intensity", "Moderate"),
            "readiness": data.get("readiness", "80%"),
            "risk": data.get("risk", "Low"),
            "notes": data.get("notes", "AI Analyzed Session")
        }
        workout_logs[user].insert(0, new_entry)
        return jsonify({"success": True, "logs": workout_logs[user]})
    
    return jsonify({"logs": workout_logs[user]})

if __name__ == '__main__':
    app.run(debug=True, port=5000)