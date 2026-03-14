import os
import json
from flask import Flask, render_template, request, redirect, url_for, Response

app = Flask(__name__)
ACTIVITY = {1:1.2, 2:1.375, 3:1.465, 4:1.55, 5:1.725, 6:1.9}
FEEDBACK_FILE = '/tmp/feedbacks.json'

def load_feedbacks():
    try:
        if os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

def save_feedback(fb):
    feedbacks = load_feedbacks()
    feedbacks.insert(0, fb)
    try:
        with open(FEEDBACK_FILE, 'w') as f:
            json.dump(feedbacks, f)
    except:
        pass

def calc_calories(weight_kg, cm, age, gender, activity, goal):
    bmr = (10*weight_kg + 6.25*cm - 5*age + (5 if gender=="male" else -161))
    maint = int(round(bmr * ACTIVITY.get(activity, 1.375)))
    protein = int(round(weight_kg * 2))
    fat     = int(round(weight_kg * 0.8))
    carbs   = int(round((maint - protein*4 - fat*9) / 4))
    r = {"maint": maint, "protein": protein, "carbs": carbs, "fat": fat, "goal": goal}
    if goal == 2:
        r["mild"]    = maint - 250
        r["loss"]    = maint - 500
        r["extreme"] = maint - 1000
    elif goal == 3:
        r["lean"]       = maint + 250
        r["moderate"]   = maint + 500
        r["aggressive"] = maint + 750
    return r

def calc_bodytype(wrist, cm):
    ratio = wrist / cm
    ratio_str = f"{ratio:.4f}"
    if ratio < 0.10:
        return {
            "name": "Ectomorph",
            "cls": "ec",
            "icon": "🦴",
            "tagline": "Lean frame with a fast metabolism — you struggle to gain weight",
            "description": "Ectomorphs have a <strong>light and lean bone structure</strong> with a naturally fast metabolism. Your body burns calories quickly, which makes it harder to gain both fat and muscle. You likely have narrow shoulders, a flat chest, and small joints.",
            "characteristics": "You have <strong>long limbs</strong> relative to your body, find it hard to gain weight even when eating a lot, have low body fat naturally, and may feel you lack strength compared to others. The good news — with the right training and nutrition, ectomorphs can build an impressive physique.",
            "wrist": wrist,
            "height_cm": round(cm, 1),
            "ratio": ratio_str
        }
    elif 0.10 <= ratio <= 0.11:
        return {
            "name": "Mesomorph",
            "cls": "ms",
            "icon": "💪",
            "tagline": "Athletic build with balanced metabolism — you respond well to training",
            "description": "Mesomorphs have a <strong>naturally athletic and muscular frame</strong>. Your body responds exceptionally well to exercise and you can gain muscle or lose fat with relative ease. You have medium-sized joints and bones with a well-proportioned figure.",
            "characteristics": "You gain <strong>muscle quickly</strong> when you train, lose fat relatively easily when you diet, have good strength and endurance, and your body adapts fast to new workouts. Mesomorphs are considered to have the most favorable body type for fitness and athletics.",
            "wrist": wrist,
            "height_cm": round(cm, 1),
            "ratio": ratio_str
        }
    else:
        return {
            "name": "Endomorph",
            "cls": "en",
            "icon": "🏋️",
            "tagline": "Solid and strong frame — you gain weight easily but also have great strength",
            "description": "Endomorphs have a <strong>wider and heavier bone structure</strong> with a naturally slower metabolism. Your body tends to store fat more easily, especially around the midsection. However, you also have great potential for strength and power.",
            "characteristics": "You gain weight <strong>easily but also have natural strength</strong>, have wider hips and shoulders, a slower metabolism, and may find it harder to lose fat. With consistent training and a controlled diet, endomorphs can become incredibly strong and build a powerful physique.",
            "wrist": wrist,
            "height_cm": round(cm, 1),
            "ratio": ratio_str
        }

# ══ ROUTES ══

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/calculator", methods=["GET","POST"])
def index():
    result = error = None
    if request.method == "POST":
        try:
            wu = int(request.form["weight_unit"])
            w  = float(request.form["weight"])
            w_kg = w * 0.453592 if wu == 2 else w
            hu = int(request.form["height_unit"])
            if hu == 1:
                feet = float(request.form.get("feet") or 0)
                inch = float(request.form.get("inch") or 0)
                cm = feet * 30.48 + inch * 2.54
            else:
                cm = float(request.form["cm_h"])
            age      = int(request.form["age"])
            activity = int(request.form["activity"])
            gender   = request.form["gender"].strip().lower()
            goal     = int(request.form["goal"])
            if w_kg <= 0 or cm <= 0 or age <= 0:
                error = "Please enter valid positive numbers."
            elif gender not in ("male","female"):
                error = "Please select a valid gender."
            else:
                result = calc_calories(w_kg, cm, age, gender, activity, goal)
        except:
            error = "Please fill in all fields correctly."
    return render_template("index.html", result=result, error=error)

@app.route("/bodytype", methods=["GET","POST"])
def bodytype():
    result = error = None
    if request.method == "POST":
        try:
            wrist = float(request.form["wrist"])
            hu = int(request.form["height_unit"])
            if hu == 1:
                feet = float(request.form.get("feet") or 0)
                inch = float(request.form.get("inch") or 0)
                cm = feet * 30.48 + inch * 2.54
            else:
                cm = float(request.form["cm_h"])
            if wrist <= 0 or cm <= 0:
                error = "Please enter valid measurements."
            else:
                result = calc_bodytype(wrist, cm)
        except:
            error = "Please fill in all fields correctly."
    return render_template("bodytype.html", result=result, error=error)

@app.route("/feedback", methods=["GET","POST"])
def feedback():
    if request.method == "POST":
        msg = request.form.get("message","").strip()
        if msg:
            save_feedback({
                "name":   request.form.get("name","Anonymous").strip() or "Anonymous",
                "rating": request.form.get("rating","5"),
                "msg":    msg
            })
        return redirect(url_for('feedback_thanks'))
    return render_template("feedback.html", sent=False, feedbacks=load_feedbacks())

@app.route("/feedback/thanks")
def feedback_thanks():
    return render_template("feedback.html", sent=True, feedbacks=load_feedbacks())


def make_meal_plan(kcal, goal, total_meals=4):
    # All food items for loss and gain
    loss_foods = {
        "breakfast": [
            {"em":"🥚","name":"Boiled Eggs","portion":"3 large eggs","cal":234,"macro":"P: 18g  F: 15g"},
            {"em":"🍞","name":"Brown Bread","portion":"1 slice (30g)","cal":80,"macro":"C: 15g  F: 1g"},
            {"em":"🥛","name":"Skimmed Milk","portion":"1 cup","cal":83,"macro":"P: 8g  C: 12g"},
        ],
        "lunch": [
            {"em":"🍗","name":"Grilled Chicken Breast","portion":"150g cooked","cal":248,"macro":"P: 46g  F: 5g"},
            {"em":"🍚","name":"Brown Rice","portion":"½ cup cooked","cal":108,"macro":"C: 22g  P: 2g"},
            {"em":"🥗","name":"Mixed Salad","portion":"1 large bowl","cal":45,"macro":"C: 9g  F: 0g"},
        ],
        "snack1": [
            {"em":"🥜","name":"Almonds","portion":"20g","cal":116,"macro":"P: 4g  F: 10g"},
            {"em":"🍎","name":"Apple","portion":"1 medium","cal":95,"macro":"C: 25g  F: 0g"},
        ],
        "snack2": [
            {"em":"🍵","name":"Green Tea","portion":"1 cup","cal":2,"macro":"0g"},
            {"em":"🥒","name":"Cucumber & Hummus","portion":"1 cup + 2 tbsp","cal":100,"macro":"C: 10g  P: 4g"},
        ],
        "dinner": [
            {"em":"🐟","name":"Grilled Fish","portion":"150g","cal":200,"macro":"P: 34g  F: 6g"},
            {"em":"🥦","name":"Steamed Broccoli","portion":"1 cup","cal":55,"macro":"C: 11g  P: 4g"},
            {"em":"🫘","name":"Lentil Soup (Daal)","portion":"1 cup","cal":140,"macro":"P: 9g  C: 24g"},
        ],
        "snack3": [
            {"em":"🫐","name":"Mixed Berries","portion":"1 cup","cal":70,"macro":"C: 18g  F: 0g"},
            {"em":"🧀","name":"Low-fat Cottage Cheese","portion":"100g","cal":98,"macro":"P: 11g  F: 4g"},
        ],
    }
    gain_foods = {
        "breakfast": [
            {"em":"🥚","name":"Scrambled Eggs","portion":"4 large eggs","cal":312,"macro":"P: 24g  F: 20g"},
            {"em":"🍞","name":"Brown Bread","portion":"2 slices","cal":160,"macro":"C: 30g  F: 2g"},
            {"em":"🥛","name":"Whole Milk","portion":"1 cup","cal":149,"macro":"P: 8g  C: 12g  F: 8g"},
            {"em":"🍌","name":"Banana","portion":"1 medium","cal":105,"macro":"C: 27g  P: 1g"},
        ],
        "lunch": [
            {"em":"🍗","name":"Chicken Breast","portion":"200g cooked","cal":330,"macro":"P: 62g  F: 7g"},
            {"em":"🍚","name":"White Rice","portion":"1 cup cooked","cal":206,"macro":"C: 45g  P: 4g"},
            {"em":"🫘","name":"Daal (Lentils)","portion":"1 cup","cal":140,"macro":"P: 9g  C: 24g"},
        ],
        "snack1": [
            {"em":"🥜","name":"Peanut Butter","portion":"2 tbsp","cal":190,"macro":"P: 8g  F: 16g"},
            {"em":"🍞","name":"Brown Bread","portion":"1 slice","cal":80,"macro":"C: 15g  F: 1g"},
            {"em":"🥛","name":"Whole Milk","portion":"1 cup","cal":149,"macro":"P: 8g  C: 12g"},
        ],
        "snack2": [
            {"em":"🍌","name":"Banana","portion":"1 large","cal":121,"macro":"C: 31g  P: 1g"},
            {"em":"🧀","name":"Cottage Cheese","portion":"100g","cal":98,"macro":"P: 11g  F: 4g"},
        ],
        "dinner": [
            {"em":"🍗","name":"Chicken Karahi / Curry","portion":"200g chicken","cal":350,"macro":"P: 40g  F: 18g"},
            {"em":"🍚","name":"Rice or 2 Rotis","portion":"1 cup / 2 rotis","cal":240,"macro":"C: 50g  P: 6g"},
            {"em":"🥗","name":"Raita / Salad","portion":"1 bowl","cal":60,"macro":"P: 3g  C: 6g"},
        ],
        "snack3": [
            {"em":"🥛","name":"Protein Shake / Milk","portion":"1 cup + oats","cal":200,"macro":"P: 10g  C: 30g"},
            {"em":"🥜","name":"Mixed Nuts","portion":"30g","cal":180,"macro":"P: 5g  F: 16g"},
        ],
    }

    foods = loss_foods if goal == "loss" else gain_foods

    # Build meal list based on count
    meal_schedule = {
        3: [
            ("🌅","Breakfast","7:00 – 8:00 AM","breakfast"),
            ("☀️","Lunch","12:30 – 1:30 PM","lunch"),
            ("🌙","Dinner","7:00 – 8:00 PM","dinner"),
        ],
        4: [
            ("🌅","Breakfast","7:00 – 8:00 AM","breakfast"),
            ("☀️","Lunch","12:30 – 1:30 PM","lunch"),
            ("🌤️","Snack","4:00 – 5:00 PM","snack1"),
            ("🌙","Dinner","7:00 – 8:00 PM","dinner"),
        ],
        5: [
            ("🌅","Breakfast","7:00 – 8:00 AM","breakfast"),
            ("🌤️","Mid Morning Snack","10:00 – 10:30 AM","snack1"),
            ("☀️","Lunch","1:00 – 2:00 PM","lunch"),
            ("🌆","Afternoon Snack","4:30 – 5:00 PM","snack2"),
            ("🌙","Dinner","7:30 – 8:30 PM","dinner"),
        ],
        6: [
            ("🌅","Breakfast","7:00 – 8:00 AM","breakfast"),
            ("🌤️","Morning Snack","10:00 AM","snack1"),
            ("☀️","Lunch","1:00 PM","lunch"),
            ("🌆","Afternoon Snack","3:30 PM","snack2"),
            ("🌇","Pre-Workout","6:00 PM","snack3"),
            ("🌙","Dinner","8:30 PM","dinner"),
        ],
    }

    schedule = meal_schedule.get(total_meals, meal_schedule[4])

    # Calculate per-meal calories
    meals_out = []
    total_base = sum(
        sum(i["cal"] for i in foods[key])
        for _, _, _, key in schedule
    )
    scale = kcal / total_base if total_base > 0 else 1

    for icon, name, time, key in schedule:
        items = foods[key]
        scaled = [{"em":i["em"],"name":i["name"],"portion":i["portion"],
                   "cal":max(1,int(i["cal"]*scale)),"macro":i["macro"]} for i in items]
        meals_out.append({
            "icon": icon,
            "name": name,
            "time": time,
            "foods": scaled,
            "total_cal": sum(i["cal"] for i in scaled)
        })

    if goal == "loss":
        tip_title = "Fat Loss Tip"
        tip = "Keep your <strong>protein high</strong> and carbs moderate. High protein keeps you full and preserves muscle during fat loss. Drink 2.5–3 liters of water daily and avoid sugary drinks."
        goal_label = "🔥 Cut"
        goal_sub = "Fat Loss"
    else:
        tip_title = "Muscle Gain Tip"
        tip = "Eat in a <strong>calorie surplus</strong> with high protein and carbs. Carbs fuel workouts and recovery. Eat biggest meal after training. Aim for at least <strong>1.6g protein per kg</strong> bodyweight daily."
        goal_label = "💪 Bulk"
        goal_sub = "Muscle Gain"

    return {
        "kcal": kcal,
        "goal_label": goal_label,
        "goal_sub": goal_sub,
        "meals": meals_out,
        "total_meals": total_meals,
        "tip_title": tip_title,
        "tip": tip
    }


@app.route("/mealplan", methods=["GET","POST"])
def mealplan():
    result = error = None
    if request.method == "POST":
        try:
            kcal = int(float(request.form["kcal"]))
            goal = request.form["goal"]
            meals = int(request.form.get("meals", 4))
            if kcal < 800 or kcal > 6000:
                error = "Please enter a calorie amount between 800 and 6000."
            elif goal not in ("loss","gain"):
                error = "Please select a goal."
            elif meals not in (3,4,5,6):
                error = "Please select number of meals."
            else:
                result = make_meal_plan(kcal, goal, meals)
        except:
            error = "Please fill in all fields correctly."
    return render_template("mealplan.html", result=result, error=error)

@app.route("/sitemap.xml")
def sitemap():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://myfitcalorie.vercel.app/</loc><priority>1.0</priority></url>
  <url><loc>https://myfitcalorie.vercel.app/calculator</loc><priority>0.9</priority></url>
  <url><loc>https://myfitcalorie.vercel.app/bodytype</loc><priority>0.9</priority></url>
</urlset>"""
    return Response(xml, mimetype='application/xml')

@app.route("/robots.txt")
def robots():
    txt = "User-agent: *\nAllow: /\nSitemap: https://myfitcalorie.vercel.app/sitemap.xml"
    return Response(txt, mimetype='text/plain')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=True)
