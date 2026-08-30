from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app, supports_credentials=True)

DATA_DIR = "/app/data"
DATABASE_NAME = os.path.join(DATA_DIR, "student5.db")


def get_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/evaluations")
def list_evaluations():
    conn = get_db()
    filters = []
    params = []

    if request.args.get("user_id"):
        filters.append("User_Id = ?")
        params.append(int(request.args["user_id"]))
    if request.args.get("status"):
        val = request.args["status"]
        if val == "in_progress":
            filters.append("Evaluation_FinalRecommendation IS NULL")
        elif val == "decided":
            filters.append("Evaluation_FinalRecommendation IS NOT NULL")
    if request.args.get("recommendation"):
        filters.append("Evaluation_FinalRecommendation = ?")
        params.append(request.args["recommendation"])
    if request.args.get("application_id"):
        filters.append("Application_Id = ?")
        params.append(int(request.args["application_id"]))

    where = " WHERE " + " AND ".join(filters) if filters else ""
    rows = conn.execute(f"SELECT * FROM evaluations{where} ORDER BY updated_at DESC", params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/evaluations/<int:evaluation_id>")
def get_evaluation(evaluation_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM evaluations WHERE Evaluation_Id = ?", (evaluation_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Evaluation not found"}), 404
    return jsonify(dict(row))


@app.post("/evaluations")
def create_evaluation():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    required = ["Application_Id", "User_Id", "HR_Staff_Name", "HR_Staff_Number"]
    for field in required:
        if field not in data or data[field] is None or data[field] == "":
            return jsonify({"error": f"{field} is required"}), 400

    score_fields = ["Evaluation_TechnicalScore", "Evaluation_EducationScore",
                    "Evaluation_CommunicationScore", "Evaluation_ProblemSolvingScore",
                    "Evaluation_ProfessionalismScore"]
    scores = []
    for f in score_fields:
        val = data.get(f)
        if val is not None and val != "":
            val = int(val)
            if val < 1 or val > 5:
                return jsonify({"error": "Scores must be between 1 and 5"}), 400
            scores.append(val)
        else:
            scores.append(None)

    rec = data.get("Evaluation_FinalRecommendation") or None
    if rec == "":
        rec = None

    if rec is not None:
        if rec not in ("Hire", "Reject"):
            return jsonify({"error": "Decision must be Hire or Reject"}), 400
        if any(s is None for s in scores):
            return jsonify({"error": "All scores are required to finalize an evaluation"}), 400

    filled = [s for s in scores if s is not None]
    overall = round(sum(filled) / len(filled), 2) if filled else None

    conn = get_db()
    existing = conn.execute("SELECT Evaluation_Id FROM evaluations WHERE Application_Id = ?",
                           (data["Application_Id"],)).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "An evaluation already exists for this application"}), 409

    now = datetime.utcnow().isoformat()

    cursor = conn.execute("""
        INSERT INTO evaluations (
            Application_Id, User_Id, HR_Staff_Name, HR_Staff_Number,
            Evaluation_TechnicalScore, Evaluation_EducationScore,
            Evaluation_CommunicationScore, Evaluation_ProblemSolvingScore,
            Evaluation_ProfessionalismScore, Evaluation_OverallScore,
            Evaluation_FinalRecommendation,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["Application_Id"], data["User_Id"],
        data["HR_Staff_Name"], data["HR_Staff_Number"],
        scores[0], scores[1], scores[2], scores[3], scores[4],
        overall, rec,
        now, now
    ))
    conn.commit()
    row = conn.execute("SELECT * FROM evaluations WHERE Evaluation_Id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.put("/evaluations/<int:evaluation_id>")
def update_evaluation(evaluation_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    conn = get_db()
    existing = conn.execute("SELECT * FROM evaluations WHERE Evaluation_Id = ?", (evaluation_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Evaluation not found"}), 404

    score_fields = [
        "Evaluation_TechnicalScore", "Evaluation_EducationScore",
        "Evaluation_CommunicationScore", "Evaluation_ProblemSolvingScore",
        "Evaluation_ProfessionalismScore",
    ]
    scores = []
    for f in score_fields:
        val = data.get(f, existing[f])
        if val is not None and val != "":
            val = int(val)
            if val < 1 or val > 5:
                conn.close()
                return jsonify({"error": "Scores must be between 1 and 5"}), 400
            scores.append(val)
        else:
            scores.append(None)

    rec = data.get("Evaluation_FinalRecommendation", existing["Evaluation_FinalRecommendation"])
    if rec == "":
        rec = None

    if rec is not None:
        if rec not in ("Hire", "Reject"):
            conn.close()
            return jsonify({"error": "Decision must be Hire or Reject"}), 400
        if any(s is None for s in scores):
            conn.close()
            return jsonify({"error": "All scores are required to finalize an evaluation"}), 400

    filled = [s for s in scores if s is not None]
    overall = round(sum(filled) / len(filled), 2) if filled else None
    now = datetime.utcnow().isoformat()

    conn.execute("""
        UPDATE evaluations SET
            HR_Staff_Name = ?, HR_Staff_Number = ?,
            Evaluation_TechnicalScore = ?, Evaluation_EducationScore = ?,
            Evaluation_CommunicationScore = ?, Evaluation_ProblemSolvingScore = ?,
            Evaluation_ProfessionalismScore = ?, Evaluation_OverallScore = ?,
            Evaluation_FinalRecommendation = ?,
            updated_at = ?
        WHERE Evaluation_Id = ?
    """, (
        data.get("HR_Staff_Name", existing["HR_Staff_Name"]),
        data.get("HR_Staff_Number", existing["HR_Staff_Number"]),
        scores[0], scores[1], scores[2], scores[3], scores[4],
        overall,
        rec,
        now, evaluation_id
    ))
    conn.commit()
    row = conn.execute("SELECT * FROM evaluations WHERE Evaluation_Id = ?", (evaluation_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))


@app.delete("/evaluations/<int:evaluation_id>")
def delete_evaluation(evaluation_id):
    conn = get_db()
    existing = conn.execute("SELECT * FROM evaluations WHERE Evaluation_Id = ?", (evaluation_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Evaluation not found"}), 404
    if existing["Evaluation_FinalRecommendation"] is not None:
        conn.close()
        return jsonify({"error": "Finalized evaluations cannot be deleted"}), 403
    conn.execute("DELETE FROM evaluations WHERE Evaluation_Id = ?", (evaluation_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Evaluation deleted"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "6005")), debug=True)
