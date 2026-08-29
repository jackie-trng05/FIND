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
        filters.append("Evaluation_Status = ?")
        params.append(request.args["status"])
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

    required = ["Application_Id", "User_Id",
                "Evaluation_TechnicalScore", "Evaluation_EducationScore",
                "Evaluation_CommunicationScore", "Evaluation_ProblemSolvingScore",
                "Evaluation_ProfessionalismScore", "Evaluation_FinalRecommendation"]
    for field in required:
        if field not in data or data[field] is None or data[field] == "":
            return jsonify({"error": f"{field} is required"}), 400

    conn = get_db()
    existing = conn.execute("SELECT Evaluation_Id FROM evaluations WHERE Application_Id = ?",
                           (data["Application_Id"],)).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "An evaluation already exists for this application"}), 409

    scores = [int(data["Evaluation_TechnicalScore"]), int(data["Evaluation_EducationScore"]),
              int(data["Evaluation_CommunicationScore"]), int(data["Evaluation_ProblemSolvingScore"]),
              int(data["Evaluation_ProfessionalismScore"])]
    for s in scores:
        if s < 1 or s > 5:
            conn.close()
            return jsonify({"error": "Scores must be between 1 and 5"}), 400

    overall = round(sum(scores) / len(scores), 2)
    now = datetime.utcnow().isoformat()
    status = data.get("Evaluation_Status", "Draft")
    if status not in ("Draft", "Completed"):
        status = "Draft"

    cursor = conn.execute("""
        INSERT INTO evaluations (
            Application_Id, User_Id,
            Evaluation_TechnicalScore, Evaluation_EducationScore,
            Evaluation_CommunicationScore, Evaluation_ProblemSolvingScore,
            Evaluation_ProfessionalismScore, Evaluation_OverallScore,
            Evaluation_FinalRecommendation,
            Evaluation_Status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["Application_Id"], data["User_Id"],
        scores[0], scores[1], scores[2], scores[3], scores[4],
        overall, data["Evaluation_FinalRecommendation"],
        status, now, now
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

    scores = [
        int(data.get("Evaluation_TechnicalScore", existing["Evaluation_TechnicalScore"])),
        int(data.get("Evaluation_EducationScore", existing["Evaluation_EducationScore"])),
        int(data.get("Evaluation_CommunicationScore", existing["Evaluation_CommunicationScore"])),
        int(data.get("Evaluation_ProblemSolvingScore", existing["Evaluation_ProblemSolvingScore"])),
        int(data.get("Evaluation_ProfessionalismScore", existing["Evaluation_ProfessionalismScore"])),
    ]
    for s in scores:
        if s < 1 or s > 5:
            conn.close()
            return jsonify({"error": "Scores must be between 1 and 5"}), 400

    overall = round(sum(scores) / len(scores), 2)
    now = datetime.utcnow().isoformat()
    status = data.get("Evaluation_Status", existing["Evaluation_Status"])
    if status not in ("Draft", "Completed"):
        status = existing["Evaluation_Status"]

    conn.execute("""
        UPDATE evaluations SET
            Evaluation_TechnicalScore = ?, Evaluation_EducationScore = ?,
            Evaluation_CommunicationScore = ?, Evaluation_ProblemSolvingScore = ?,
            Evaluation_ProfessionalismScore = ?, Evaluation_OverallScore = ?,
            Evaluation_FinalRecommendation = ?,
            Evaluation_Status = ?, updated_at = ?
        WHERE Evaluation_Id = ?
    """, (
        scores[0], scores[1], scores[2], scores[3], scores[4],
        overall,
        data.get("Evaluation_FinalRecommendation", existing["Evaluation_FinalRecommendation"]),
        status, now, evaluation_id
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
    if existing["Evaluation_Status"] == "Completed":
        conn.close()
        return jsonify({"error": "Completed evaluations cannot be deleted"}), 403
    conn.execute("DELETE FROM evaluations WHERE Evaluation_Id = ?", (evaluation_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Evaluation deleted"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "6005")), debug=True)
