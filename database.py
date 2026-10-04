import sqlite3
from datetime import datetime, date

DB_NAME = "attendance.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # جدول الإعدادات
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)
        
        # جدول الموظفين (تم إضافة عمود device_id)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            employee_code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            job_title TEXT,
            phone TEXT,
            active INTEGER DEFAULT 1,
            device_id TEXT
        )
        """)
        
        # جدول الحضور والانصراف
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_code TEXT,
            name TEXT,
            action TEXT,
            timestamp DATETIME,
            latitude REAL,
            longitude REAL,
            distance_m REAL,
            accuracy_m REAL,
            FOREIGN KEY (employee_code) REFERENCES employees (employee_code)
        )
        """)
        conn.commit()

# --- إدارة الإعدادات ---
def get_setting(key, default=""):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

def set_setting(key, value):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()

# --- إدارة الموظفين ---
def normalize_code(code):
    if not code:
        return ""
    return str(code).strip().zfill(3)

def add_employee(code, name, job_title="", phone=""):
    code = normalize_code(code)
    if not code or not name:
        return False, "يرجى إدخال كود واسم الموظف."
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT employee_code FROM employees WHERE employee_code = ?", (code,))
        if cursor.fetchone():
            return False, "كود الموظف مستخدم بالفعل."
        
        cursor.execute(
            "INSERT INTO employees (employee_code, name, job_title, phone, active) VALUES (?, ?, ?, ?, 1)",
            (code, name, job_title, phone)
        )
        conn.commit()
        return True, "تمت إضافة الموظف بنجاح."

def get_employee(code, active_only=True):
    code = normalize_code(code)
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM employees WHERE employee_code = ?"
        if active_only:
            query += " AND active = 1"
        cursor.execute(query, (code,))
        row = cursor.fetchone()
        return dict(row) if row else None

def list_employees():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees ORDER BY employee_code ASC")
        return [dict(row) for row in cursor.fetchall()]

def update_employee(code, name, job_title, phone):
    code = normalize_code(code)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE employees SET name = ?, job_title = ?, phone = ? WHERE employee_code = ?",
            (name, job_title, phone, code)
        )
        conn.commit()
        return True

def set_employee_active(code, active_status):
    code = normalize_code(code)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE employees SET active = ? WHERE employee_code = ?", (1 if active_status else 0, code))
        conn.commit()

def delete_employee(code):
    code = normalize_code(code)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM employees WHERE employee_code = ?", (code,))
        conn.commit()

# --- إدارة وحماية أجهزة الموظفين ---
def register_employee_device(code, device_id):
    """ربط كود الموظف ببصمة جهازه المحمول"""
    code = normalize_code(code)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE employees SET device_id = ? WHERE employee_code = ?", (device_id, code))
        conn.commit()

def verify_employee_device(code, current_device_id):
    """التحقق من مطابقة جهاز الموظف مع الجهاز المسجل"""
    code = normalize_code(code)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT device_id FROM employees WHERE employee_code = ?", (code,))
        row = cursor.fetchone()
        if not row:
            return False, "الموظف غير موجود."
        
        registered_device = row["device_id"]
        
        # ربط تلقائي عند أول تسجيل للموظف
        if not registered_device:
            register_employee_device(code, current_device_id)
            return True, "تم ربط هذا الهاتف بحسابك بنجاح."
        
        # مطابقة الجهاز الحالي مع الجهاز المسجل
        if registered_device == current_device_id:
            return True, "الجهاز مطابق."
        
        return False, "عذراً! لا يمكنك تسجيل الحضور إلا من الهاتف المسجل باسمك."

# --- إدارة الحضور والانصراف ---
def record_attendance(employee, action, lat, lon, dist, accuracy):
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO attendance (employee_code, name, action, timestamp, latitude, longitude, distance_m, accuracy_m)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (employee["employee_code"], employee["name"], action, now, lat, lon, dist, accuracy))
        conn.commit()

def today_records(code):
    code = normalize_code(code)
    today_str = date.today().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT action, timestamp, distance_m FROM attendance 
            WHERE employee_code = ? AND date(timestamp) = ? 
            ORDER BY id DESC
        """, (code, today_str))
        return [dict(row) for row in cursor.fetchall()]

def stats_today():
    today_str = date.today().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM employees")
        total = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) as active FROM employees WHERE active = 1")
        active = cursor.fetchone()["active"]
        
        cursor.execute("SELECT COUNT(DISTINCT employee_code) as present FROM attendance WHERE date(timestamp) = ? AND action = 'حضور'", (today_str,))
        present = cursor.fetchone()["present"]
        
        cursor.execute("SELECT COUNT(DISTINCT employee_code) as departed FROM attendance WHERE date(timestamp) = ? AND action = 'انصراف'", (today_str,))
        departed = cursor.fetchone()["departed"]
        
        return {"total": total, "active": active, "present": present, "departed": departed}

def attendance_report(start_date, end_date, code_filter=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT employee_code as "كود الموظف", name as "اسم الموظف", action as "العملية", 
                   timestamp as "التاريخ والوقت", distance_m as "المسافة (متر)"
            FROM attendance 
            WHERE date(timestamp) BETWEEN ? AND ?
        """
        params = [start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")]
        if code_filter:
            query += " AND employee_code = ?"
            params.append(normalize_code(code_filter))
            
        query += " ORDER BY timestamp DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
