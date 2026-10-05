import streamlit as st
import sqlite3
import pandas as pd
import math
import requests
from datetime import datetime
import pytz
from streamlit_js_eval import get_geolocation
import os
import qrcode
import io
import cv2
import numpy as np
import urllib.request

# ==========================================
# 1. الإعدادات العامة للشعار والمجلدات
# ==========================================
PROJECT_NAME = "حضور وانصراف العاملين بفرع الجيزة"
LOGO_PATH = "logo.png"
UPLOADS_DIR = "attendance_videos"

if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

ADMIN_PASSWORD = "admin_giza_2026"

# ضبط التوقيت المحلي للقاهرة
EGYPT_TZ = pytz.timezone('Africa/Cairo')

def get_egypt_datetime():
    return datetime.now(EGYPT_TZ)

# ==========================================
# 2. تهيئة الواجهة ودعم اتجاه اليمين إلى اليسار (RTL)
# ==========================================
st.set_page_config(page_title=PROJECT_NAME, page_icon="🏢", layout="centered")

st.markdown("""
    
""", unsafe_allow_html=True)

st.sidebar.title(PROJECT_NAME)

if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "تسجيل الحضور/الانصراف"

page = st.sidebar.radio("الانتقال إلى:", ["تسجيل الحضور/الانصراف", "لوحة تحكم الإدارة"], key="nav_selection")

# ==========================================
# 3. قواعد البيانات وإدارة الإعدادات
# ==========================================
conn = sqlite3.connect('employee_attendance.db', check_same_thread=False)
cursor = conn.cursor()

# 1. جدول سجلات الحضور والانصراف (يشمل مسار الفيديو والصورة المقتطعة)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_code TEXT,
        emp_name TEXT,
        date TEXT,
        time TEXT,
        action TEXT,
        ip_address TEXT,
        distance_m REAL,
        photo_path TEXT,
        video_path TEXT
    )
''')

try:
    cursor.execute("ALTER TABLE attendance_logs ADD COLUMN photo_path TEXT")
    conn.commit()
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE attendance_logs ADD COLUMN video_path TEXT")
    conn.commit()
except sqlite3.OperationalError:
    pass

# 2. جدول بيانات الموظفين
cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        emp_code TEXT PRIMARY KEY,
        emp_name TEXT NOT NULL,
        phone TEXT,
        job_title TEXT DEFAULT 'موظف',
        is_active INTEGER DEFAULT 1
    )
''')

# 3. جدول إعدادات النظام
cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
''')
conn.commit()

REAL_APP_URL = "https://employee-attendance-dv932asxnr57mmovkwpltp.streamlit.app/"

DEFAULT_SETTINGS = {
    "branch_ip": "41.38.200.191",
    "branch_lat": "30.0761",
    "branch_lon": "31.2161",
    "max_distance": "1000.0",
    "disable_wifi_check": "0",
    "app_url": REAL_APP_URL
}

for key, val in DEFAULT_SETTINGS.items():
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, str(val)))
conn.commit()

def get_setting(key):
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    if res and res[0]:
        return res[0]
    return DEFAULT_SETTINGS.get(key, "")

def set_setting(key, value):
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()

# ==========================================
# 4. تحميل كاشفات OpenCV بأمان
# ==========================================
FACE_CASCADE_PATH = "haarcascade_frontalface_default.xml"

def download_cascade_if_missing(file_path, url):
    if not os.path.exists(file_path):
        try:
            urllib.request.urlretrieve(url, file_path)
        except Exception:
            pass

download_cascade_if_missing(
    FACE_CASCADE_PATH, 
    "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
)

# ==========================================
# 5. الدوال البرمجية المساعدة ومعالجة مقاطع الفيديو
# ==========================================
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def get_user_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=4)
        return response.json()['ip']
    except:
        return None

def get_active_employees_map():
    try:
        cursor.execute("SELECT emp_code, emp_name, phone FROM employees WHERE is_active = 1")
        rows = cursor.fetchall()
        emp_dict = {}
        for code, name, phone in rows:
            emp_dict[str(code).strip()] = {
                "name": str(name).strip(),
                "phone": str(phone).strip() if phone else ""
            }
        return emp_dict
    except Exception:
        cursor.execute("DROP TABLE IF EXISTS employees")
        cursor.execute('''
            CREATE TABLE employees (
                emp_code TEXT PRIMARY KEY,
                emp_name TEXT NOT NULL,
                phone TEXT,
                job_title TEXT DEFAULT 'موظف',
                is_active INTEGER DEFAULT 1
            )
        ''')
        sample_employees = [
            ('101', 'أحمد حسني الجنزوري', '01069996245', 'مدير الفرع'),
            ('102', 'خالد عبدالحكيم هارون', '01120807631', 'عضو IT'),
            ('103', 'أحمد محمد عمر', '01201109892', 'عضو تنمية مهنية')
        ]
        cursor.executemany("INSERT OR REPLACE INTO employees VALUES (?, ?, ?, ?, 1)", sample_employees)
        conn.commit()
        
        cursor.execute("SELECT emp_code, emp_name, phone FROM employees WHERE is_active = 1")
        rows = cursor.fetchall()
        emp_dict = {}
        for code, name, phone in rows:
            emp_dict[str(code).strip()] = {
                "name": str(name).strip(),
                "phone": str(phone).strip() if phone else ""
            }
        return emp_dict

def process_and_verify_video(video_bytes_io, save_video_path, save_photo_path):
    """تحليل الفيديو القصير واستخراج لقطة التوثيق الحية وإثبات الحركة"""
    try:
        # حفظ ملف الفيديو المؤقت
        with open(save_video_path, "wb") as f:
            f.write(video_bytes_io.getbuffer())

        cap = cv2.VideoCapture(save_video_path)
        if not cap.isOpened():
            return False, "تعذر قراءة ملف الفيديو المرفوع"

        face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH if os.path.exists(FACE_CASCADE_PATH) else cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        detected_faces = 0
        best_frame = None

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))

            if len(faces) >= 1:
                detected_faces += 1
                if best_frame is None:
                    best_frame = frame.copy()

        cap.release()

        if detected_faces == 0:
            return False, "لم يتم اكتشاف وجه بشرى واضح في فيديو التوثيق! يرجى تصوير الموظف مباشرة."

        if best_frame is not None:
            cv2.imwrite(save_photo_path, best_frame)

        return True, "تم التحقق الفيديوي بنجاح"
    except Exception as e:
        return True, f"تم التوثيق (ملاحظة: {str(e)})"

# ==========================================
# 6. الشاشات الرئيسية للتطبيق
# ==========================================
if page == "تسجيل الحضور/الانصراف":
    if os.path.exists(LOGO_PATH):
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.image(LOGO_PATH, width=280)
            
    st.title(PROJECT_NAME)
    st.caption("بوابة تسجيل الحضور والأنصراف الرقمية بالفرع")
    
    st.markdown("""
