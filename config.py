import os


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "your_mysql_password"),
    "database": os.getenv("DB_NAME", "ami_db"),
}
