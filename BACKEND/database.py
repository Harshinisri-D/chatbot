import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "meditrain_ai"),
}

# Function to establish a connection
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Initialize database (create table)
def init_db():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            doctor_id INT NOT NULL,
            chat_history TEXT NOT NULL,
            score INT NOT NULL,
            feedback TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.commit()
    cursor.close()
    connection.close()

# Function to log chat session
def log_session(doctor_id, chat_history, score, feedback):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO chat_sessions (doctor_id, chat_history, score, feedback) VALUES (%s, %s, %s, %s)",
            (doctor_id, chat_history, score, feedback),
        )
        connection.commit()
    except Exception as e:
        print(f"Database Logging Error: {e}")
    finally:
        cursor.close()
        connection.close()

# Function to fetch sessions for a doctor
def get_sessions(doctor_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM chat_sessions WHERE doctor_id = %s ORDER BY timestamp DESC", (doctor_id,))
    sessions = cursor.fetchall()
    cursor.close()
    connection.close()
    return sessions

# Initialize database on startup
init_db()
