# 1. Create MySQL database:
#    CREATE DATABASE ami_db;
#
# 2. Update config.py with your MySQL credentials
#
# 3. Install dependencies:
#    pip install -r requirements.txt
#
# 4. Run seed script (creates tables + loads 100 patients):
#    python seed_db.py
#
# 5. Start Flask server:
#    python app.py
#
# 6. Open browser at http://localhost:5000

from decimal import Decimal

import mysql.connector
from flask import Flask, jsonify, render_template, request
from mysql.connector import Error

from config import DB_CONFIG


app = Flask(__name__)

MARKER_FIELDS = [
    "wbc",
    "neu",
    "neu_ly",
    "pdw",
    "mpv_ly",
    "ly",
    "mo",
    "ba",
    "plt_ly",
    "mpv",
]
REQUIRED_PATIENT_FIELDS = [
    "patient_name",
    "age",
    "gender",
    "ami_status",
    "doctor_id",
    "hospital_id",
    *MARKER_FIELDS,
]
ALLOWED_GENDERS = {"Male", "Female", "Other"}
PATIENT_SUMMARY_QUERY = """
    SELECT
        p.patient_id,
        p.patient_name,
        p.age,
        p.gender,
        p.ami_status,
        p.doctor_id,
        p.hospital_id,
        d.doctor_name,
        d.speciality,
        h.hospital_name,
        h.city,
        h.state
    FROM patients p
    JOIN doctors d
        ON p.doctor_id = d.doctor_id
       AND p.hospital_id = d.hospital_id
    JOIN hospitals h
        ON p.hospital_id = h.hospital_id
"""


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def decimal_to_number(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


def normalize_patient_row(row):
    normalized = {}
    for key, value in row.items():
        normalized[key] = decimal_to_number(value)
    return normalized


def validate_patient_payload(payload):
    missing_fields = [field for field in REQUIRED_PATIENT_FIELDS if payload.get(field) in (None, "")]
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}", None

    cleaned = {}
    cleaned["patient_name"] = str(payload["patient_name"]).strip()
    if not cleaned["patient_name"]:
        return False, "Patient name cannot be empty.", None

    try:
        cleaned["age"] = int(payload["age"])
    except (TypeError, ValueError):
        return False, "Age must be an integer.", None
    if cleaned["age"] < 1 or cleaned["age"] > 120:
        return False, "Age must be between 1 and 120.", None

    cleaned["gender"] = str(payload["gender"]).strip()
    if cleaned["gender"] not in ALLOWED_GENDERS:
        return False, "Gender must be Male, Female, or Other.", None

    try:
        cleaned["ami_status"] = int(payload["ami_status"])
    except (TypeError, ValueError):
        return False, "AMI status must be 0 or 1.", None
    if cleaned["ami_status"] not in (0, 1):
        return False, "AMI status must be 0 or 1.", None

    for field in ("doctor_id", "hospital_id"):
        try:
            cleaned[field] = int(payload[field])
        except (TypeError, ValueError):
            return False, f"{field} must be an integer.", None

    for field in MARKER_FIELDS:
        try:
            cleaned[field] = float(payload[field])
        except (TypeError, ValueError):
            return False, f"{field} must be a numeric value.", None

    return True, None, cleaned


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/hospitals", methods=["GET"])
def get_hospitals():
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT hospital_id, hospital_name, city, state, phone
            FROM hospitals
            ORDER BY hospital_name
            """
        )
        hospitals = [normalize_patient_row(row) for row in cursor.fetchall()]
        return jsonify(hospitals)
    except Error as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/api/doctors", methods=["GET"])
def get_doctors():
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT d.doctor_id, d.doctor_name, d.speciality, d.phone, d.hospital_id, h.hospital_name
            FROM doctors d
            JOIN hospitals h ON d.hospital_id = h.hospital_id
            ORDER BY d.doctor_name
            """
        )
        doctors = [normalize_patient_row(row) for row in cursor.fetchall()]
        return jsonify(doctors)
    except Error as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/api/doctors/<int:hospital_id>", methods=["GET"])
def get_doctors_by_hospital(hospital_id):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT doctor_id, doctor_name, speciality, phone, hospital_id
            FROM doctors
            WHERE hospital_id = %s
            ORDER BY doctor_name
            """,
            (hospital_id,),
        )
        doctors = [normalize_patient_row(row) for row in cursor.fetchall()]
        return jsonify(doctors)
    except Error as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/api/patients", methods=["GET"])
def get_patients():
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        patient_name = request.args.get("name", "").strip()
        if patient_name:
            cursor.execute(
                f"""
                {PATIENT_SUMMARY_QUERY}
                WHERE LOWER(p.patient_name) = LOWER(%s)
                ORDER BY p.patient_id
                """,
                (patient_name,),
            )
        else:
            cursor.execute(
                f"""
                {PATIENT_SUMMARY_QUERY}
                ORDER BY p.patient_id
                """
            )

        patients = [normalize_patient_row(row) for row in cursor.fetchall()]
        return jsonify(patients)
    except Error as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/api/patients/<int:patient_id>", methods=["GET"])
def get_patient_detail(patient_id):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                p.patient_id,
                p.patient_name,
                p.age,
                p.gender,
                p.ami_status,
                p.wbc,
                p.neu,
                p.neu_ly,
                p.pdw,
                p.mpv_ly,
                p.ly,
                p.mo,
                p.ba,
                p.plt_ly,
                p.mpv,
                p.doctor_id,
                p.hospital_id,
                d.doctor_name,
                d.speciality,
                h.hospital_name,
                h.city,
                h.state
            FROM patients p
            JOIN doctors d
                ON p.doctor_id = d.doctor_id
               AND p.hospital_id = d.hospital_id
            JOIN hospitals h ON p.hospital_id = h.hospital_id
            WHERE p.patient_id = %s
            """,
            (patient_id,),
        )
        patient = cursor.fetchone()
        if not patient:
            return jsonify({"success": False, "error": "Patient not found."}), 404
        return jsonify(normalize_patient_row(patient))
    except Error as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/api/patients", methods=["POST"])
def create_patient():
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"success": False, "error": "Request body must be valid JSON."}), 400

    is_valid, error_message, cleaned = validate_patient_payload(payload)
    if not is_valid:
        return jsonify({"success": False, "error": error_message}), 400

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT hospital_id FROM hospitals WHERE hospital_id = %s",
            (cleaned["hospital_id"],),
        )
        if not cursor.fetchone():
            return jsonify({"success": False, "error": "Selected hospital does not exist."}), 400

        cursor.execute(
            """
            SELECT doctor_id
            FROM doctors
            WHERE doctor_id = %s AND hospital_id = %s
            """,
            (cleaned["doctor_id"], cleaned["hospital_id"]),
        )
        if not cursor.fetchone():
            return jsonify(
                {"success": False, "error": "Selected doctor does not belong to the selected hospital."}
            ), 400

        cursor.execute(
            """
            INSERT INTO patients (
                patient_name, age, gender, ami_status, wbc, neu, neu_ly, pdw,
                mpv_ly, ly, mo, ba, plt_ly, mpv, doctor_id, hospital_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                cleaned["patient_name"],
                cleaned["age"],
                cleaned["gender"],
                cleaned["ami_status"],
                cleaned["wbc"],
                cleaned["neu"],
                cleaned["neu_ly"],
                cleaned["pdw"],
                cleaned["mpv_ly"],
                cleaned["ly"],
                cleaned["mo"],
                cleaned["ba"],
                cleaned["plt_ly"],
                cleaned["mpv"],
                cleaned["doctor_id"],
                cleaned["hospital_id"],
            ),
        )
        connection.commit()
        return jsonify({"success": True, "patient_id": cursor.lastrowid})
    except Error as exc:
        if connection and connection.is_connected():
            connection.rollback()
        return jsonify({"success": False, "error": str(exc)}), 400
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    app.run(debug=True)
