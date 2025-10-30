import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from src.config import DATA_DIR

DB_FILE = DATA_DIR / "exam_scheduler.db"


class Database:
    
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_FILE
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()
    
    def execute(self, query, params=None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            raise Exception(f"Database execute error: {e}")
    
    def execute_many(self, query, params_list):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                conn.commit()
        except sqlite3.Error as e:
            raise Exception(f"Database execute_many error: {e}")
    
    def fetch_one(self, query, params=None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                return cursor.fetchone()
        except sqlite3.Error as e:
            raise Exception(f"Database fetch_one error: {e}")
    
    def fetch_all(self, query, params=None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                return cursor.fetchall()
        except sqlite3.Error as e:
            raise Exception(f"Database fetch_all error: {e}")
    
    def create_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'coordinator')),
                    is_active INTEGER DEFAULT 1,
                    department_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (department_id) REFERENCES departments(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS departments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    code TEXT UNIQUE NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS classrooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    department_id INTEGER NOT NULL,
                    capacity INTEGER NOT NULL,
                    rows INTEGER NOT NULL,
                    columns INTEGER NOT NULL,
                    seating_arrangement INTEGER NOT NULL DEFAULT 2,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (department_id) REFERENCES departments(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    instructor TEXT,
                    department_id INTEGER,
                    class_level TEXT,
                    is_mandatory INTEGER DEFAULT 1,
                    default_duration INTEGER DEFAULT 75,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (department_id) REFERENCES departments(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_number TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    department_id INTEGER NOT NULL,
                    class_level TEXT,
                    email TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (department_id) REFERENCES departments(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS student_courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    course_id INTEGER NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(student_id, course_id),
                    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exam_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    start_date DATE,
                    end_date DATE,
                    allowed_days TEXT,
                    default_exam_duration INTEGER DEFAULT 75,
                    default_break_duration INTEGER DEFAULT 15,
                    min_days_between_exams INTEGER DEFAULT 0,
                    created_by INTEGER NOT NULL,
                    is_finalized INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_id INTEGER NOT NULL,
                    course_id INTEGER NOT NULL,
                    exam_date DATE,
                    start_time TIME,
                    duration INTEGER NOT NULL DEFAULT 75,
                    student_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'scheduled',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (schedule_id) REFERENCES exam_schedules(id) ON DELETE CASCADE,
                    FOREIGN KEY (course_id) REFERENCES courses(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exam_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_id INTEGER NOT NULL,
                    classroom_id INTEGER NOT NULL,
                    allocated_seats INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
                    FOREIGN KEY (classroom_id) REFERENCES classrooms(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exam_proctors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_session_id INTEGER NOT NULL,
                    proctor_name TEXT NOT NULL,
                    role TEXT DEFAULT 'proctor',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (exam_session_id) REFERENCES exam_sessions(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS seating_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_session_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    row_number INTEGER NOT NULL,
                    column_number INTEGER NOT NULL,
                    seat_number INTEGER NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (exam_session_id) REFERENCES exam_sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id) REFERENCES students(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS import_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    total_rows INTEGER DEFAULT 0,
                    success_rows INTEGER DEFAULT 0,
                    error_rows INTEGER DEFAULT 0,
                    error_details TEXT,
                    imported_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            print("[OK] Tüm tablolar oluşturuldu (Raw SQL)")
    
    def drop_all_tables(self):
        tables = [
            'import_logs', 'seating_assignments', 'exam_proctors', 'exam_sessions', 'exams',
            'exam_schedules', 'student_courses', 'students', 
            'courses', 'classrooms', 'departments', 'users'
        ]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
            conn.commit()
            print("[OK] Tüm tablolar silindi")


_db_instance = None

def get_db():
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def init_db_raw():
    db = get_db()
    db.create_tables()
    return db
