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
import random

# ==========================================
# 1. الإعدادات العامة للشعار والمجلدات
# ==========================================
PROJECT_NAME = "حضور وانصراف العاملين بفرع الجيزة"
LOGO_PATH = "logo.png"
UPLOADS_DIR = "attendance_selfies"

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

# 1. جدول سجلات الحضور والانصراف
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
        photo_path TEXT
    )
''')

try:
    cursor.execute("ALTER TABLE attendance_logs ADD COLUMN photo_path TEXT")
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
# 4. تحميل كاشفات ملامح الوجه بأمان
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
# 5. الدوال البرمجية المساعدة
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

def analyze_photo_has_face(image_bytes):
    """فحص كشف ملامح الوجه البشري"""
    try:
        file_bytes = np.asarray(bytearray(image_bytes.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None:
            return False, "الصورة الملتقطة غير صالحة"
            
        if os.path.exists(FACE_CASCADE_PATH):
            face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))
            
            if len(faces) == 0:
                return False, "لم يتم اكتشاف وجه بشري واضح بالصورة! يرجى إظهار الوجه أمام الكاميرا."
            elif len(faces) > 1:
                return False, "تم اكتشاف أكثر من وجه بالصورة! يرجى توجيه الكاميرا للموظف فقط."
                
        return True, "تم الفحص بنجاح"
    except Exception:
        return True, "تم الحفظ بنجاح"

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
    
    # توليد كود حيوية عشوائي لكل جلسة
    if "liveness_code" not in st.session_state:
        st.session_state["liveness_code"] = str(random.randint(100, 999))
        
    current_code = st.session_state["liveness_code"]

    branch_public_ip = get_setting("branch_ip")
    branch_lat = float(get_setting("branch_lat"))
    branch_lon = float(get_setting("branch_lon"))
    max_distance_meters = float(get_setting("max_distance"))
    disable_wifi_check = get_setting("disable_wifi_check") == "1"
    
    user_ip = get_user_ip()
    loc = get_geolocation()
    active_employees = get_active_employees_map()

    if loc and 'coords' in loc and user_ip:
        user_lat = loc['coords']['latitude']
        user_lon = loc['coords']['longitude']
        distance = calculate_distance(branch_lat, branch_lon, user_lat, user_lon)
        
        is_wifi_ok = True if disable_wifi_check else (user_ip == branch_public_ip)
        is_gps_ok = (distance <= max_distance_meters)
        
        if not is_wifi_ok:
            st.error(f"⛔ تعذر التسجيل: أنت غير متصل بشبكة Wi-Fi الفرع! (عنوان IP الحالي: {user_ip})")
        elif not is_gps_ok:
            st.error(f"⛔ تعذر التسجيل: موقعك يبعد بـ {int(distance)}m عن الفرع. النطاق المسموح: {int(max_distance_meters)}m")
        else:
            st.success("✅ تم التحقق من الموقع وشبكة الفرع بنجاح!")
            
            emp_code_input = st.text_input("أدخل كود الموظف المخصص لك:", placeholder="مثال: 101")
            action_type = st.radio("نوع الحركة:", ["تسجيل حضور", "تسجيل انصراف"])
            
            st.markdown(f"""
