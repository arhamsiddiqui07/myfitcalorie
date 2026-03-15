import os
import json
from flask import Flask, render_template, request, redirect, url_for, Response

app = Flask(__name__)

ACTIVITY = {1: 1.2, 2: 1.375, 3: 1.465, 4: 1.55, 5: 1.725, 6: 1.9}
FEEDBACK_FILE = '/tmp/mfc_feedbacks.json'

# ─── Helpers ───────────────────────────────────────────────

def load_feedbacks():
    try:
        if os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_feedback(item):
    data = load_feedbacks()
    data.insert(0, item)
    try:
        with open(FEEDBACK_FILE, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

# ─── Calculators ───────────────────────────────────────────

def calc_calories(weight_kg, height_cm, age, gender, activity, goal):
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + (5 if gender == 'male' else -161)
    maint = int(round(bmr * ACTIVITY.get(activity, 1.375)))
    protein = int(round(weight_kg * 2))
    fat = int(round(weight_kg * 0.8))
    carbs = max(0, int(round((maint - protein * 4 - fat * 9) / 4)))
    r = {'maint': maint, 'protein': protein, 'carbs': carbs, 'fat': fat, 'goal': goal}
    if goal == 2:
        r['mild'] = maint - 250
        r['loss'] = maint - 500
        r['extreme'] = maint - 1000
    elif goal == 3:
        r['lean'] = maint + 250
        r['moderate'] = maint + 500
        r['aggressive'] = maint + 750
    return r

def calc_bodytype(wrist_cm, height_cm):
    ratio = wrist_cm / height_cm
    if ratio < 0.10:
        return {
            'name': 'Ectomorph', 'cls': 'ec', 'icon': '🦴',
            'tagline': 'Lean frame with a fast metabolism — you struggle to gain weight',
            'description': 'Ectomorphs have a <strong>light and lean bone structure</strong> with a naturally fast metabolism. Your body burns calories quickly, making it harder to gain both fat and muscle. You likely have narrow shoulders, a flat chest, and small joints.',
            'characteristics': 'You have <strong>long limbs</strong> relative to your body, find it hard to gain weight even when eating a lot, have naturally low body fat, and may feel you lack strength. With the right training and nutrition, ectomorphs can build an impressive physique.',
            'wrist': wrist_cm, 'height_cm': round(height_cm, 1), 'ratio': f'{ratio:.4f}'
        }
    elif ratio <= 0.11:
        return {
            'name': 'Mesomorph', 'cls': 'ms', 'icon': '💪',
            'tagline': 'Athletic build with balanced metabolism — you respond well to training',
            'description': 'Mesomorphs have a <strong>naturally athletic and muscular frame</strong>. Your body responds exceptionally well to exercise and you can gain muscle or lose fat with relative ease. You have medium-sized joints and a well-proportioned figure.',
            'characteristics': 'You gain <strong>muscle quickly</strong> when you train, lose fat relatively easily when you diet, have good strength and endurance, and your body adapts fast to new workouts. Mesomorphs are considered to have the most favorable body type for fitness.',
            'wrist': wrist_cm, 'height_cm': round(height_cm, 1), 'ratio': f'{ratio:.4f}'
        }
    else:
        return {
            'name': 'Endomorph', 'cls': 'en', 'icon': '🏋️',
            'tagline': 'Solid and strong frame — you gain weight easily but also have great strength',
            'description': 'Endomorphs have a <strong>wider and heavier bone structure</strong> with a naturally slower metabolism. Your body tends to store fat more easily, especially around the midsection. However, you also have great potential for strength and power.',
            'characteristics': 'You gain weight <strong>easily but also have natural strength</strong>, have wider hips and shoulders, a slower metabolism, and may find it harder to lose fat. With consistent training and controlled diet, endomorphs can become incredibly strong.',
            'wrist': wrist_cm, 'height_cm': round(height_cm, 1), 'ratio': f'{ratio:.4f}'
        }

def calc_mealplan(kcal, goal, total_meals):
    loss_foods = {
        'breakfast': [
            {'em': '🥚', 'name': 'Boiled Eggs', 'portion': '3 large eggs', 'cal': 234, 'macro': 'P: 18g  F: 15g'},
            {'em': '🍞', 'name': 'Brown Bread', 'portion': '1 slice (30g)', 'cal': 80, 'macro': 'C: 15g  F: 1g'},
            {'em': '🥛', 'name': 'Skimmed Milk', 'portion': '1 cup (240ml)', 'cal': 83, 'macro': 'P: 8g  C: 12g'},
        ],
        'lunch': [
            {'em': '🍗', 'name': 'Grilled Chicken Breast', 'portion': '150g cooked', 'cal': 248, 'macro': 'P: 46g  F: 5g'},
            {'em': '🍚', 'name': 'Brown Rice', 'portion': '½ cup cooked', 'cal': 108, 'macro': 'C: 22g  P: 2g'},
            {'em': '🥗', 'name': 'Mixed Salad', 'portion': '1 large bowl', 'cal': 45, 'macro': 'C: 9g  F: 0g'},
        ],
        'snack1': [
            {'em': '🥜', 'name': 'Almonds', 'portion': '20g (handful)', 'cal': 116, 'macro': 'P: 4g  F: 10g'},
            {'em': '🍎', 'name': 'Apple', 'portion': '1 medium', 'cal': 95, 'macro': 'C: 25g  F: 0g'},
        ],
        'snack2': [
            {'em': '🥒', 'name': 'Cucumber & Hummus', 'portion': '1 cup + 2 tbsp', 'cal': 100, 'macro': 'C: 10g  P: 4g'},
            {'em': '🍵', 'name': 'Green Tea', 'portion': '1 cup', 'cal': 2, 'macro': '0g'},
        ],
        'dinner': [
            {'em': '🐟', 'name': 'Grilled Fish', 'portion': '150g', 'cal': 200, 'macro': 'P: 34g  F: 6g'},
            {'em': '🥦', 'name': 'Steamed Broccoli', 'portion': '1 cup', 'cal': 55, 'macro': 'C: 11g  P: 4g'},
            {'em': '🫘', 'name': 'Lentil Soup (Daal)', 'portion': '1 cup', 'cal': 140, 'macro': 'P: 9g  C: 24g'},
        ],
        'snack3': [
            {'em': '🫐', 'name': 'Mixed Berries', 'portion': '1 cup', 'cal': 70, 'macro': 'C: 18g  F: 0g'},
            {'em': '🧀', 'name': 'Low-fat Cottage Cheese', 'portion': '100g', 'cal': 98, 'macro': 'P: 11g  F: 4g'},
        ],
    }
    gain_foods = {
        'breakfast': [
            {'em': '🥚', 'name': 'Scrambled Eggs', 'portion': '4 large eggs', 'cal': 312, 'macro': 'P: 24g  F: 20g'},
            {'em': '🍞', 'name': 'Brown Bread', 'portion': '2 slices (60g)', 'cal': 160, 'macro': 'C: 30g  F: 2g'},
            {'em': '🥛', 'name': 'Whole Milk', 'portion': '1 cup (240ml)', 'cal': 149, 'macro': 'P: 8g  C: 12g  F: 8g'},
            {'em': '🍌', 'name': 'Banana', 'portion': '1 medium', 'cal': 105, 'macro': 'C: 27g  P: 1g'},
        ],
        'lunch': [
            {'em': '🍗', 'name': 'Chicken Breast', 'portion': '200g cooked', 'cal': 330, 'macro': 'P: 62g  F: 7g'},
            {'em': '🍚', 'name': 'White Rice', 'portion': '1 cup cooked', 'cal': 206, 'macro': 'C: 45g  P: 4g'},
            {'em': '🫘', 'name': 'Daal (Lentils)', 'portion': '1 cup', 'cal': 140, 'macro': 'P: 9g  C: 24g'},
        ],
        'snack1': [
            {'em': '🥜', 'name': 'Peanut Butter', 'portion': '2 tbsp', 'cal': 190, 'macro': 'P: 8g  F: 16g'},
            {'em': '🍞', 'name': 'Brown Bread', 'portion': '1 slice', 'cal': 80, 'macro': 'C: 15g  F: 1g'},
            {'em': '🥛', 'name': 'Whole Milk', 'portion': '1 cup', 'cal': 149, 'macro': 'P: 8g  C: 12g'},
        ],
        'snack2': [
            {'em': '🍌', 'name': 'Banana', 'portion': '1 large', 'cal': 121, 'macro': 'C: 31g  P: 1g'},
            {'em': '🧀', 'name': 'Cottage Cheese', 'portion': '100g', 'cal': 98, 'macro': 'P: 11g  F: 4g'},
        ],
        'dinner': [
            {'em': '🍗', 'name': 'Chicken Karahi / Curry', 'portion': '200g chicken', 'cal': 350, 'macro': 'P: 40g  F: 18g'},
            {'em': '🍚', 'name': 'Rice or 2 Rotis', 'portion': '1 cup / 2 rotis', 'cal': 240, 'macro': 'C: 50g  P: 6g'},
            {'em': '🥗', 'name': 'Raita / Salad', 'portion': '1 bowl', 'cal': 60, 'macro': 'P: 3g  C: 6g'},
        ],
        'snack3': [
            {'em': '🥛', 'name': 'Protein Shake / Milk + Oats', 'portion': '1 cup + 50g oats', 'cal': 200, 'macro': 'P: 10g  C: 30g'},
            {'em': '🥜', 'name': 'Mixed Nuts', 'portion': '30g', 'cal': 180, 'macro': 'P: 5g  F: 16g'},
        ],
    }

    schedule_map = {
        3: [('🌅','Breakfast','7:00–8:00 AM','breakfast'),('☀️','Lunch','12:30–1:30 PM','lunch'),('🌙','Dinner','7:00–8:00 PM','dinner')],
        4: [('🌅','Breakfast','7:00–8:00 AM','breakfast'),('☀️','Lunch','12:30–1:30 PM','lunch'),('🌤️','Snack','4:00–5:00 PM','snack1'),('🌙','Dinner','7:00–8:00 PM','dinner')],
        5: [('🌅','Breakfast','7:00–8:00 AM','breakfast'),('🌤️','Mid-Morning Snack','10:00–10:30 AM','snack1'),('☀️','Lunch','1:00–2:00 PM','lunch'),('🌆','Afternoon Snack','4:30–5:00 PM','snack2'),('🌙','Dinner','7:30–8:30 PM','dinner')],
        6: [('🌅','Breakfast','7:00–8:00 AM','breakfast'),('🌤️','Morning Snack','10:00 AM','snack1'),('☀️','Lunch','1:00 PM','lunch'),('🌆','Afternoon Snack','3:30 PM','snack2'),('🌇','Pre-Workout','6:00 PM','snack3'),('🌙','Dinner','8:30 PM','dinner')],
    }

    foods = loss_foods if goal == 'loss' else gain_foods
    schedule = schedule_map.get(total_meals, schedule_map[4])

    base_total = sum(sum(i['cal'] for i in foods[key]) for _, _, _, key in schedule)
    scale = kcal / base_total if base_total > 0 else 1

    meals = []
    for icon, name, time, key in schedule:
        scaled = [dict(i, cal=max(1, int(i['cal'] * scale))) for i in foods[key]]
        meals.append({'icon': icon, 'name': name, 'time': time, 'foods': scaled, 'total_cal': sum(i['cal'] for i in scaled)})

    if goal == 'loss':
        tip_title = 'Fat Loss Tip'
        tip = 'Keep your <strong>protein high</strong> and carbs moderate. High protein keeps you full longer and preserves muscle while you lose fat. Drink 2.5–3 liters of water daily and avoid sugary drinks.'
        goal_label = '🔥 Fat Loss'
        goal_sub = 'Cutting'
    else:
        tip_title = 'Muscle Gain Tip'
        tip = 'Eat in a <strong>calorie surplus</strong> with high protein and carbs. Carbs fuel workouts and muscle recovery. Eat your biggest meal after training. Aim for at least <strong>1.6g protein per kg</strong> bodyweight daily.'
        goal_label = '💪 Muscle Gain'
        goal_sub = 'Bulking'

    return {'kcal': kcal, 'goal_label': goal_label, 'goal_sub': goal_sub,
            'meals': meals, 'total_meals': total_meals, 'tip_title': tip_title, 'tip': tip}

# ─── Routes ────────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/calculator', methods=['GET', 'POST'])
def calculator():
    result = error = None
    if request.method == 'POST':
        try:
            wu = int(request.form['weight_unit'])
            w = float(request.form['weight'])
            w_kg = w * 0.453592 if wu == 2 else w
            hu = int(request.form['height_unit'])
            if hu == 1:
                feet = float(request.form.get('feet') or 0)
                inch = float(request.form.get('inch') or 0)
                cm = feet * 30.48 + inch * 2.54
            else:
                cm = float(request.form['cm_h'])
            age = int(request.form['age'])
            activity = int(request.form['activity'])
            gender = request.form['gender'].strip().lower()
            goal = int(request.form['goal'])
            if w_kg <= 0 or cm <= 0 or age <= 0:
                error = 'Please enter valid positive numbers.'
            elif gender not in ('male', 'female'):
                error = 'Please select a valid gender.'
            else:
                result = calc_calories(w_kg, cm, age, gender, activity, goal)
        except Exception:
            error = 'Please fill in all fields correctly.'
    return render_template('calculator.html', result=result, error=error)

@app.route('/bodytype', methods=['GET', 'POST'])
def bodytype():
    result = error = None
    if request.method == 'POST':
        try:
            wrist = float(request.form['wrist'])
            hu = int(request.form['height_unit'])
            if hu == 1:
                feet = float(request.form.get('feet') or 0)
                inch = float(request.form.get('inch') or 0)
                cm = feet * 30.48 + inch * 2.54
            else:
                cm = float(request.form['cm_h'])
            if wrist <= 0 or cm <= 0:
                error = 'Please enter valid measurements.'
            else:
                result = calc_bodytype(wrist, cm)
        except Exception:
            error = 'Please fill in all fields correctly.'
    return render_template('bodytype.html', result=result, error=error)

@app.route('/mealplan', methods=['GET', 'POST'])
def mealplan():
    result = error = None
    if request.method == 'POST':
        try:
            kcal = int(float(request.form['kcal']))
            goal = request.form['goal']
            meals = int(request.form.get('meals', 4))
            if kcal < 800 or kcal > 6000:
                error = 'Please enter calories between 800 and 6000.'
            elif goal not in ('loss', 'gain'):
                error = 'Please select a goal.'
            elif meals not in (3, 4, 5, 6):
                error = 'Please select number of meals.'
            else:
                result = calc_mealplan(kcal, goal, meals)
        except Exception:
            error = 'Please fill in all fields correctly.'
    return render_template('mealplan.html', result=result, error=error)

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        msg = request.form.get('message', '').strip()
        if msg:
            save_feedback({
                'name': request.form.get('name', 'Anonymous').strip() or 'Anonymous',
                'rating': request.form.get('rating', '5'),
                'msg': msg
            })
        return redirect(url_for('feedback_thanks'))
    return render_template('feedback.html', sent=False, feedbacks=load_feedbacks())

@app.route('/feedback/thanks')
def feedback_thanks():
    return render_template('feedback.html', sent=True, feedbacks=load_feedbacks())


def calc_ffmi(weight_kg, height_cm, body_fat_pct):
    height_m = height_cm / 100
    fat_mass = weight_kg * (body_fat_pct / 100)
    lean_mass = weight_kg - fat_mass
    ffmi = lean_mass / (height_m ** 2)
    # Normalized FFMI (adjusted to 1.8m height)
    ffmi_norm = ffmi + 6.1 * (1.8 - height_m)

    if ffmi_norm < 17:
        level = 'Beginner'
        desc = 'Low muscle mass. Great time to start strength training!'
        cls = 're'
    elif ffmi_norm < 20:
        level = 'Average Fitness'
        desc = 'Average muscle mass. Consistent training will help you progress.'
        cls = 'ye'
    elif ffmi_norm < 22:
        level = 'Good Physique'
        desc = 'Good muscular development. You are visibly athletic.'
        cls = 'bl'
    elif ffmi_norm < 24:
        level = 'Very Muscular'
        desc = 'Very muscular — approaching natural limits. Excellent work!'
        cls = 'gr'
    else:
        level = 'Elite / Near Natural Limit'
        desc = 'Elite level physique. At or beyond the natural genetic ceiling for most people.'
        cls = 'or'

    return {
        'weight_kg': round(weight_kg, 1),
        'height_cm': round(height_cm, 1),
        'bf_pct': body_fat_pct,
        'lean_mass': round(lean_mass, 1),
        'fat_mass': round(fat_mass, 1),
        'ffmi': round(ffmi, 1),
        'ffmi_norm': round(ffmi_norm, 1),
        'level': level,
        'desc': desc,
        'cls': cls,
    }


@app.route('/ffmi', methods=['GET', 'POST'])
def ffmi():
    result = error = None
    if request.method == 'POST':
        try:
            wu = int(request.form['weight_unit'])
            w = float(request.form['weight'])
            w_kg = w * 0.453592 if wu == 2 else w
            hu = int(request.form['height_unit'])
            if hu == 1:
                feet = float(request.form.get('feet') or 0)
                inch = float(request.form.get('inch') or 0)
                cm = feet * 30.48 + inch * 2.54
            else:
                cm = float(request.form['cm_h'])
            bf = float(request.form['body_fat'])
            if w_kg <= 0 or cm <= 0 or bf <= 0 or bf >= 60:
                error = 'Please enter valid numbers. Body fat must be between 1–60%.'
            else:
                result = calc_ffmi(w_kg, cm, bf)
        except Exception:
            error = 'Please fill in all fields correctly.'
    return render_template('ffmi.html', result=result, error=error)


# ─── Water Intake ──────────────────────────────────────────
def calc_water(weight_kg, activity, climate):
    base = weight_kg * 0.033  # liters
    act_add = {1: 0, 2: 0.35, 3: 0.5, 4: 0.7, 5: 1.0}
    climate_add = {1: 0, 2: 0.35, 3: 0.6}
    total = base + act_add.get(activity, 0) + climate_add.get(climate, 0)
    glasses = round(total / 0.25)
    return {
        'total': round(total, 1),
        'glasses': glasses,
        'base': round(base, 1),
        'weight_kg': round(weight_kg, 1),
    }

# ─── One Rep Max ───────────────────────────────────────────
def calc_1rm(weight, reps):
    # Epley formula
    if reps == 1:
        orm = weight
    else:
        orm = weight * (1 + reps / 30)
    pcts = [
        (100, orm),
        (95,  orm * 0.95),
        (90,  orm * 0.90),
        (85,  orm * 0.85),
        (80,  orm * 0.80),
        (75,  orm * 0.75),
        (70,  orm * 0.70),
    ]
    return {
        'orm': round(orm, 1),
        'weight': weight,
        'reps': reps,
        'pcts': [(p, round(v, 1)) for p, v in pcts],
    }

# ─── Workout Calorie Burn ──────────────────────────────────
EXERCISES = {
    'running':       ('🏃 Running (moderate)',        8.0),
    'running_fast':  ('🏃 Running (fast)',            11.0),
    'cycling':       ('🚴 Cycling (moderate)',         6.0),
    'cycling_fast':  ('🚴 Cycling (fast)',             10.0),
    'swimming':      ('🏊 Swimming',                   7.0),
    'weightlifting': ('🏋️ Weight Training',            4.0),
    'hiit':          ('⚡ HIIT',                        9.0),
    'walking':       ('🚶 Walking',                    3.5),
    'yoga':          ('🧘 Yoga',                       2.5),
    'boxing':        ('🥊 Boxing',                     8.5),
    'football':      ('⚽ Football / Soccer',          7.0),
    'basketball':    ('🏀 Basketball',                 6.5),
    'skipping':      ('⏭️ Jump Rope',                  10.0),
    'elliptical':    ('🔄 Elliptical',                 5.5),
    'rowing':        ('🚣 Rowing',                     7.0),
}

def calc_workout(exercise_key, weight_kg, duration_min):
    name, met = EXERCISES.get(exercise_key, ('Unknown', 5.0))
    # Calories = MET * weight_kg * duration_hr
    kcal = round(met * weight_kg * (duration_min / 60))
    return {
        'exercise': name,
        'weight_kg': round(weight_kg, 1),
        'duration': duration_min,
        'kcal': kcal,
        'kcal_per_min': round(kcal / duration_min, 1),
    }

EXERCISES_LIST = [(k, v[0]) for k, v in EXERCISES.items()]

@app.route('/water', methods=['GET', 'POST'])
def water():
    result = error = None
    if request.method == 'POST':
        try:
            wu = int(request.form['weight_unit'])
            w = float(request.form['weight'])
            w_kg = w * 0.453592 if wu == 2 else w
            activity = int(request.form['activity'])
            climate = int(request.form['climate'])
            if w_kg <= 0:
                error = 'Please enter a valid weight.'
            else:
                result = calc_water(w_kg, activity, climate)
        except Exception:
            error = 'Please fill in all fields correctly.'
    return render_template('water.html', result=result, error=error)

@app.route('/orm', methods=['GET', 'POST'])
def orm():
    result = error = None
    if request.method == 'POST':
        try:
            wu = int(request.form['weight_unit'])
            w = float(request.form['weight'])
            w_kg = w * 0.453592 if wu == 2 else w
            reps = int(request.form['reps'])
            exercise = request.form.get('exercise', 'Bench Press')
            if w_kg <= 0 or reps <= 0 or reps > 30:
                error = 'Please enter valid weight and reps (1–30).'
            else:
                result = calc_1rm(w_kg, reps)
                result['exercise_name'] = exercise
        except Exception:
            error = 'Please fill in all fields correctly.'
    return render_template('orm.html', result=result, error=error)

@app.route('/workout', methods=['GET', 'POST'])
def workout():
    result = error = None
    if request.method == 'POST':
        try:
            wu = int(request.form['weight_unit'])
            w = float(request.form['weight'])
            w_kg = w * 0.453592 if wu == 2 else w
            exercise = request.form['exercise']
            duration = int(request.form['duration'])
            if w_kg <= 0 or duration <= 0 or duration > 300:
                error = 'Please enter valid values.'
            elif exercise not in EXERCISES:
                error = 'Please select an exercise.'
            else:
                result = calc_workout(exercise, w_kg, duration)
        except Exception:
            error = 'Please fill in all fields correctly.'
    return render_template('workout.html', result=result, error=error, exercises=EXERCISES_LIST)

@app.route('/sitemap.xml')
def sitemap():
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://myfitcalorie.vercel.app/</loc><priority>1.0</priority></url>
  <url><loc>https://myfitcalorie.vercel.app/calculator</loc><priority>0.9</priority></url>
  <url><loc>https://myfitcalorie.vercel.app/bodytype</loc><priority>0.9</priority></url>
  <url><loc>https://myfitcalorie.vercel.app/mealplan</loc><priority>0.9</priority></url>
  <url><loc>https://myfitcalorie.vercel.app/ffmi</loc><priority>0.9</priority></url>
</urlset>'''
    return Response(xml, mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    return Response('User-agent: *\nAllow: /\nSitemap: https://myfitcalorie.vercel.app/sitemap.xml', mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
