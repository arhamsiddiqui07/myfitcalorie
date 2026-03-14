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
