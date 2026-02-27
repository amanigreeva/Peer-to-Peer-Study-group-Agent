"""
Flask web dashboard for the Peer-to-Peer Study Group Agent.

Run:
    python app.py
Then open:  http://127.0.0.1:5000
"""
import sys
import os
import json
import base64

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify, send_file
from models.student import Student, SUBJECTS, LEARNING_STYLES, AVAILABILITY_OPTIONS
from clustering.study_group_agent import StudyGroupAgent
from data.sample_students import generate_sample_students

app = Flask(__name__)
app.secret_key = "p2p-study-group-agent-secret"

# ------------------------------------------------------------------
# Global agent instance (in-memory for demo; use a DB for production)
# ------------------------------------------------------------------
agent = StudyGroupAgent()
_students_store: dict = {}   # id → Student
_next_id = 1

VIZ_PATH = os.path.join("static", "cluster_plot.png")


def _reload_agent():
    agent.load_students(list(_students_store.values()))


def _seed_sample_data(n: int = 20):
    global _next_id
    _next_id = 1
    _students_store.clear()
    for s in generate_sample_students(n):
        s.id = _next_id
        _students_store[_next_id] = s
        _next_id += 1
    _reload_agent()


# Seed with sample data on startup
_seed_sample_data(20)


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.route("/")
def index():
    students = [s.to_dict() for s in _students_store.values()]
    return render_template(
        "index.html",
        students=students,
        subjects=SUBJECTS,
        learning_styles=LEARNING_STYLES,
        availability_options=AVAILABILITY_OPTIONS,
        total=len(students),
    )


@app.route("/api/students", methods=["GET"])
def api_students():
    return jsonify([s.to_dict() for s in _students_store.values()])


@app.route("/api/add_student", methods=["POST"])
def add_student():
    global _next_id
    data = request.get_json(force=True)
    try:
        subjects = {subj: float(data.get(subj, 0)) for subj in SUBJECTS}
        student = Student(
            id=_next_id,
            name=data["name"].strip(),
            subjects=subjects,
            learning_style=data.get("learning_style", "Visual"),
            availability=data.get("availability", []),
            email=data.get("email", ""),
        )
        _students_store[_next_id] = student
        _next_id += 1
        _reload_agent()
        return jsonify({"success": True, "student": student.to_dict()})
    except (KeyError, ValueError) as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/remove_student/<int:sid>", methods=["DELETE"])
def remove_student(sid: int):
    if sid in _students_store:
        del _students_store[sid]
        _reload_agent()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Student not found"}), 404


@app.route("/api/form_groups", methods=["POST"])
def form_groups():
    data = request.get_json(force=True)
    method = data.get("method", "kmeans")
    n_groups = data.get("n_groups")
    if n_groups is not None:
        try:
            n_groups = int(n_groups)
        except (ValueError, TypeError):
            n_groups = None

    try:
        groups = agent.form_groups(method=method, n_groups=n_groups)
        evaluation = agent.evaluate_groups(groups)
        # Save visualisation
        agent.visualize_groups(groups, save_path=VIZ_PATH)

        # Serialise groups
        serialised = {
            gid: [s.to_dict() for s in members]
            for gid, members in groups.items()
        }
        return jsonify({
            "success": True,
            "groups": serialised,
            "evaluation": evaluation,
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/seed", methods=["POST"])
def seed():
    data = request.get_json(force=True)
    n = int(data.get("n", 20))
    _seed_sample_data(max(4, min(n, 100)))
    return jsonify({"success": True, "count": len(_students_store)})


@app.route("/static/cluster_plot.png")
def cluster_plot():
    if os.path.exists(VIZ_PATH):
        return send_file(VIZ_PATH, mimetype="image/png")
    return "", 404


if __name__ == "__main__":
    os.makedirs("static", exist_ok=True)
    app.run(debug=True, port=5000)
