import os
import json
from flask import Flask, render_template, request

app = Flask(__name__)

ACTIVITY = {1:1.2, 2:1.375, 3:1.465, 4:1.55, 5:1.725, 6:1.9}

# Feedback file path - saves permanently
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
    feedbacks.append(fb)
    try:
        with open(FEEDBACK_FILE, 'w') as f:
            json.dump(feedbacks, f)
    except:
        pass
    return feedbacks

def calc(weight_kg, cm, age, gender, activity, goal):
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

@app.route("/", methods=["GET","POST"])
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
                result = calc(w_kg, cm, age, gender, activity, goal)
        except:
            error = "Please fill in all fields correctly."
    return render_template("index.html", result=result, error=error)

@app.route("/feedback", methods=["GET","POST"])
def feedback():
    sent = False
    if request.method == "POST":
        msg = request.form.get("message","").strip()
        if msg:
            save_feedback({
                "name":   request.form.get("name","Anonymous").strip() or "Anonymous",
                "rating": request.form.get("rating","5"),
                "msg":    msg
            })
            sent = True
    feedbacks = load_feedbacks()
    return render_template("feedback.html", sent=sent, feedbacks=feedbacks)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=True)
