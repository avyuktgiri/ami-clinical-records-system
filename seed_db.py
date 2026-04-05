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
    ("Dr. Karan Bedi", "Cardiology", "080-4100-1303", 1),
    ("Dr. Priya Nair", "General Medicine", "080-4100-1304", 1),
    ("Dr. Rohan Malhotra", "Cardiology", "080-4100-1305", 1),
    ("Dr. Sneha Kapoor", "Emergency Medicine", "040-3888-2302", 2),
    ("Dr. Arjun Rao", "Cardiology", "040-3888-2303", 2),
    ("Dr. Kavya Shah", "Internal Medicine", "040-3888-2304", 2),
    ("Dr. Manish Tandon", "Cardiology", "044-4555-3403", 3),
    ("Dr. Isha Kulkarni", "General Medicine", "044-4555-3404", 3),
    ("Dr. Dev Patel", "Emergency Medicine", "044-4555-3405", 3),
    ("Dr. Tanvi Chawla", "Cardiology", "044-4555-3406", 3),
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
RANDOM_SEED = 42
MALE_FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Ishaan", "Reyansh",
    "Arjun", "Krish", "Rohan", "Kunal", "Dev",
    "Atharv", "Vihaan", "Siddharth", "Harsh", "Lakshya",
    "Pranav", "Yash", "Aniket", "Nikhil", "Manav",
]
FEMALE_FIRST_NAMES = [
    "Aanya", "Diya", "Ira", "Kiara", "Myra",
    "Naina", "Riya", "Sara", "Tara", "Zoya",
    "Anaya", "Meera", "Kavya", "Navya", "Ishita",
    "Trisha", "Anika", "Pihu", "Saanvi", "Prisha",
]
LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Reddy", "Kapoor",
    "Nair", "Iyer", "Gupta", "Mehta", "Bhat",
    "Kulkarni", "Joshi", "Chauhan", "Malhotra", "Saxena",
    "Desai", "Pandey", "Agarwal", "Mishra", "Menon",
]


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

    doctor_records = []
    cursor.execute("SELECT doctor_id, hospital_id FROM doctors ORDER BY doctor_id")
    for row in cursor.fetchall():
        doctor_records.append({"doctor_id": row[0], "hospital_id": row[1]})

    return hospital_ids, doctor_records


def generate_patient_name(gender, male_index, female_index):
    if gender == "Male":
        first_names = MALE_FIRST_NAMES
        sequence_index = male_index
    else:
        first_names = FEMALE_FIRST_NAMES
        sequence_index = female_index

    first_name = first_names[sequence_index % len(first_names)]
    # Spread surnames more aggressively so the first 100 rows don't cluster on a single surname.
    last_name = LAST_NAMES[(sequence_index * 3 + len(first_name)) % len(LAST_NAMES)]
    return f"{first_name} {last_name}"


def build_weighted_doctor_cycles(doctors_by_hospital):
    weighted_cycles = {}
    for hospital_id, doctor_ids in doctors_by_hospital.items():
        if len(doctor_ids) == 5:
            weighted_cycles[hospital_id] = {
                1: [
                    doctor_ids[0], doctor_ids[0], doctor_ids[0],
                    doctor_ids[1], doctor_ids[1],
                    doctor_ids[2],
                ],
                0: [
                    doctor_ids[3], doctor_ids[3], doctor_ids[3],
                    doctor_ids[4], doctor_ids[4],
                    doctor_ids[2],
                ],
            }
        elif len(doctor_ids) == 4:
            weighted_cycles[hospital_id] = {
                1: [
                    doctor_ids[0], doctor_ids[0], doctor_ids[0],
                    doctor_ids[1], doctor_ids[1],
                    doctor_ids[2],
                ],
                0: [
                    doctor_ids[3], doctor_ids[3], doctor_ids[3],
                    doctor_ids[2], doctor_ids[2],
                    doctor_ids[1],
                ],
            }
        else:
            weighted_cycles[hospital_id] = {
                1: [
                    doctor_ids[0], doctor_ids[0], doctor_ids[0],
                    doctor_ids[1], doctor_ids[1],
                    doctor_ids[2], doctor_ids[2],
                    doctor_ids[3],
                ],
                0: [
                    doctor_ids[4], doctor_ids[4], doctor_ids[4],
                    doctor_ids[5], doctor_ids[5],
                    doctor_ids[3], doctor_ids[3],
                    doctor_ids[2],
                ],
            }
    return weighted_cycles


def build_patient_rows(hospital_ids, doctor_records):
    dataframe = pd.read_excel(DATASET_PATH)
    dataframe = dataframe.rename(columns=COLUMN_MAPPING)
    rng = random.Random(RANDOM_SEED)

    doctors_by_hospital = {hospital_id: [] for hospital_id in hospital_ids}
    for record in doctor_records:
        doctors_by_hospital[record["hospital_id"]].append(record["doctor_id"])

    weighted_cycles = build_weighted_doctor_cycles(doctors_by_hospital)
    doctor_cycle_positions = {
        hospital_id: {0: 0, 1: 0} for hospital_id in hospital_ids
    }
    male_name_index = 0
    female_name_index = 0

    patient_rows = []
    for index, row in dataframe.iterrows():
        hospital_id = hospital_ids[index % len(hospital_ids)]
        ami_status = int(row["ami_status"])
        doctor_cycle = weighted_cycles[hospital_id][ami_status]
        doctor_position = doctor_cycle_positions[hospital_id][ami_status] % len(doctor_cycle)
        doctor_id = doctor_cycle[doctor_position]
        doctor_cycle_positions[hospital_id][ami_status] += 1
        gender = rng.choice(["Male", "Female"])
        patient_name = generate_patient_name(gender, male_name_index, female_name_index)
        if gender == "Male":
            male_name_index += 1
        else:
            female_name_index += 1

        patient_rows.append(
            (
                patient_name,
                rng.randint(40, 80),
                gender,
                ami_status,
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
                doctor_id,
                hospital_id,
            )
        )
    return patient_rows


def seed_patients(cursor, hospital_ids, doctor_records):
    patient_rows = build_patient_rows(hospital_ids, doctor_records)
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
        hospital_ids, doctor_records = seed_reference_data(cursor)
        seed_patients(cursor, hospital_ids, doctor_records)
        connection.commit()
        print("Database seeded successfully with 3 hospitals, 15 doctors, and 100 patients.")
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
