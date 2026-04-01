# AMI Clinical Records Management System

A full-stack AMI (Acute Myocardial Infarction) clinical records management system built with Flask, MySQL, pandas, and Bootstrap 5.

## Features

- Seeds 100 patient records from the bundled Excel dataset
- Uses exactly 3 MySQL tables: `hospitals`, `doctors`, and `patients`
- Lets users add new patients from a web interface
- Supports patient lookup by ID or exact patient name
- Shows AMI status with hospital, doctor, and blood marker details

## Project Structure

```text
dbs_research_project/
├── app.py
├── config.py
├── seed_db.py
├── ami_reduced_100.xlsx
├── requirements.txt
├── README.md
└── templates/
    └── index.html
```

## Prerequisites

- Python 3.10+
- MySQL Server

## Setup

1. Clone the repository.
2. Create the MySQL database:

```sql
CREATE DATABASE ami_db;
```

3. Set database credentials using environment variables.

macOS/Linux:

```bash
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=your_mysql_password
export DB_NAME=ami_db
```

Windows PowerShell:

```powershell
$env:DB_HOST="localhost"
$env:DB_USER="root"
$env:DB_PASSWORD="your_mysql_password"
$env:DB_NAME="ami_db"
```

4. Create and activate a virtual environment.

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

5. Install dependencies:

```bash
pip install -r requirements.txt
```

6. Seed the database:

```bash
python seed_db.py
```

7. Start the Flask app:

```bash
python app.py
```

8. Open the app in your browser:

```text
http://127.0.0.1:5000
```

## API Routes

- `GET /`
- `GET /api/hospitals`
- `GET /api/doctors`
- `GET /api/doctors/<hospital_id>`
- `GET /api/patients`
- `GET /api/patients?name=<exact_name>`
- `GET /api/patients/<patient_id>`
- `POST /api/patients`

## Notes

- `seed_db.py` is idempotent and will drop and recreate the 3 tables each time.
- The bundled Excel file is already included in the repository.
- `config.py` reads credentials from environment variables so passwords are not stored in Git.
