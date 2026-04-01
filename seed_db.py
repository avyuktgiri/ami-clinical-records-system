import random
from pathlib import Path

import mysql.connector
import pandas as pd
from mysql.connector import Error

from config import DB_CONFIG


DATASET_PATH = Path(__file__).resolve().parent / "ami_reduced_100.xlsx"

HOSPITALS = [
    ("Sunrise Heart Institute", "Bengaluru", "Karnataka", "080-4100-1200"),
    ("Riverdale Medical Center", "Hyderabad", "Telangana", "040-3888-2211"),
    ("Green Valley Hospital", "Chennai", "Tamil Nadu", "044-4555-3344"),
]

DOCTORS = [
    ("Dr. Asha Menon", "Cardiology", "080-4100-1301", 1),
    ("Dr. Rahul Khanna", "Internal Medicine", "080-4100-1302", 1),
    ("Dr. Meera Iyer", "Cardiology", "040-3888-2301", 2),
    ("Dr. Vikram Sethi", "Emergency Medicine", "044-4555-3401", 3),
    ("Dr. Nisha Verma", "Cardiology", "044-4555-3402", 3),
]

COLUMN_MAPPING = {
    "AMI_Status": "ami_status",
    "WBC": "wbc",
    "NEU": "neu",
    "NEU/LY": "neu_ly",
    "PDW": "pdw",
    "MPV/LY": "mpv_ly",
    "LY": "ly",
    "MO": "mo",
    "BA": "ba",
    "PLT/LY": "plt_ly",
    "MPV": "mpv",
}


def get_connection(include_database=True):
    config = dict(DB_CONFIG)
    if not include_database:
        config.pop("database", None)
    return mysql.connector.connect(**config)


def recreate_tables(cursor):
    cursor.execute("DROP TABLE IF EXISTS patients")
    cursor.execute("DROP TABLE IF EXISTS doctors")
    cursor.execute("DROP TABLE IF EXISTS hospitals")

    cursor.execute(
        """
        CREATE TABLE hospitals (
            hospital_id   INT AUTO_INCREMENT PRIMARY KEY,
            hospital_name VARCHAR(150) NOT NULL,
            city          VARCHAR(100),
            state         VARCHAR(100),
            phone         VARCHAR(20)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE doctors (
            doctor_id    INT AUTO_INCREMENT PRIMARY KEY,
            doctor_name  VARCHAR(150) NOT NULL,
            speciality   VARCHAR(100),
            phone        VARCHAR(20),
            hospital_id  INT NOT NULL,
            FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id)
                ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE patients (
            patient_id   INT AUTO_INCREMENT PRIMARY KEY,
            patient_name VARCHAR(150) NOT NULL,
            age          INT,
            gender       ENUM('Male', 'Female', 'Other'),
            ami_status   TINYINT NOT NULL COMMENT '0 = No AMI (Control), 1 = AMI',
            wbc          DECIMAL(6,2),
            neu          DECIMAL(6,2),
            neu_ly       DECIMAL(8,4),
            pdw          DECIMAL(6,2),
            mpv_ly       DECIMAL(8,4),
            ly           DECIMAL(6,2),
            mo           DECIMAL(6,2),
            ba           DECIMAL(6,2),
            plt_ly       DECIMAL(10,4),
            mpv          DECIMAL(6,2),
            doctor_id    INT NOT NULL,
            hospital_id  INT NOT NULL,
            FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id) ON DELETE CASCADE,
            FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE CASCADE
        )
        """
    )


def seed_reference_data(cursor):
    cursor.executemany(
        """
        INSERT INTO hospitals (hospital_name, city, state, phone)
        VALUES (%s, %s, %s, %s)
        """,
        HOSPITALS,
    )

    hospital_ids = []
    cursor.execute("SELECT hospital_id FROM hospitals ORDER BY hospital_id")
    for row in cursor.fetchall():
        hospital_ids.append(row[0])

    doctor_rows = []
    for doctor_name, speciality, phone, hospital_position in DOCTORS:
        hospital_id = hospital_ids[hospital_position - 1]
        doctor_rows.append((doctor_name, speciality, phone, hospital_id))

    cursor.executemany(
        """
        INSERT INTO doctors (doctor_name, speciality, phone, hospital_id)
        VALUES (%s, %s, %s, %s)
        """,
        doctor_rows,
    )

    doctor_ids = []
    cursor.execute("SELECT doctor_id FROM doctors ORDER BY doctor_id")
    for row in cursor.fetchall():
        doctor_ids.append(row[0])

    return hospital_ids, doctor_ids


def build_patient_rows(hospital_ids, doctor_ids):
    dataframe = pd.read_excel(DATASET_PATH)
    dataframe = dataframe.rename(columns=COLUMN_MAPPING)

    patient_rows = []
    for index, row in dataframe.iterrows():
        patient_rows.append(
            (
                f"Patient_{index + 1:03d}",
                random.randint(40, 80),
                random.choice(["Male", "Female"]),
                int(row["ami_status"]),
                float(row["wbc"]),
                float(row["neu"]),
                float(row["neu_ly"]),
                float(row["pdw"]),
                float(row["mpv_ly"]),
                float(row["ly"]),
                float(row["mo"]),
                float(row["ba"]),
                float(row["plt_ly"]),
                float(row["mpv"]),
                doctor_ids[index % len(doctor_ids)],
                hospital_ids[index % len(hospital_ids)],
            )
        )
    return patient_rows


def seed_patients(cursor, hospital_ids, doctor_ids):
    patient_rows = build_patient_rows(hospital_ids, doctor_ids)
    cursor.executemany(
        """
        INSERT INTO patients (
            patient_name, age, gender, ami_status, wbc, neu, neu_ly, pdw,
            mpv_ly, ly, mo, ba, plt_ly, mpv, doctor_id, hospital_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        patient_rows,
    )


def main():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}")

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        recreate_tables(cursor)
        hospital_ids, doctor_ids = seed_reference_data(cursor)
        seed_patients(cursor, hospital_ids, doctor_ids)
        connection.commit()
        print("Database seeded successfully with 3 hospitals, 5 doctors, and 100 patients.")
    except Error as exc:
        if connection and connection.is_connected():
            connection.rollback()
        raise RuntimeError(f"Database seeding failed: {exc}") from exc
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    main()
