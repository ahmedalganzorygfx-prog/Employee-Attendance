import streamlit as st
import sqlite3
import pandas as pd
import math
import requests
from datetime import datetime
from streamlit_js_eval import get_geolocation
import os

# ==========================================
# 1. الإعدادات العامة للشعار والفرع
# ==========================================
PROJECT_NAME = "Employee Attendance"
LOGO_PATH = "logo.png"

# إحداثيات موقع الفرع
BRANCH_LAT = 30.0444
BRANCH_LON = 31.2357
MAX_DISTANCE_METERS = 50.0

# الـ Public IP لشبكة Wi-Fi الفرع
BRANCH_PUBLIC_IP = "197.35.120.45"

# كلمة مرور الإدارة
ADMIN_PASSWORD = "123456"

# قائمة الموظفين الخمسة المعتمدين بالفرع
EMPLOYEES = {
    "01012345671": "أحمد حسني",
    "01012345672": "محمد علي",
    "01012345673": "محمود إبراهيم",
    "01012345674": "سارة أحمد",
    "01012345675": "منى يوسف"
}

# ==========================================
# 2. تهيئة الواجهة بدون شعار في الجانب
# ==========================================
st.set_page_config(page_title=PROJECT_NAME, page_icon="🏢", layout="centered")

# القائمة الجانبية النصية فقط
st.sidebar.title(f"🏢 {PROJECT_NAME}")
page = st.sidebar.radio("الانتقال إلى:", ["تسجيل الحضور/الانصراف", "لوحة تحكم الإدارة"])

# ==========================================
# 3. الدوال البرمجية وقاعدة البيانات
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

conn = sqlite3.connect('employee_attendance.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        emp_name TEXT,
        date TEXT,
        time TEXT,
        action TEXT,
        ip_address TEXT,
        distance_m REAL
    )
''')
conn.commit()

# ==========================================
# 4. الشاشات الرئيسية
# ==========================================
if page == "تسجيل الحضور/الانصراف":
    # عرض الشعار كعنصر رئيسي كبير وموسع في منتصف الصفحة
    if os.path.exists(LOGO_PATH):
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.image(LOGO_PATH, width=280)
            
    st.title(PROJECT_NAME)
    st.caption("بوابة تسجيل الحضور الذكية بالفرع")
    st.info("📲 يرجى الاتصال بـ Wi-Fi الفرع وتفعيل موقع الـ GPS بالجوال.")
    
    user_ip = get_user_ip()
    loc = get_geolocation()
    
    if loc and 'coords' in loc and user_ip:
        user_lat = loc['coords']['latitude']
        user_lon = loc['coords']['longitude']
        distance = calculate_distance(BRANCH_LAT, BRANCH_LON, user_lat, user_lon)
        
        is_wifi_ok = (user_ip == BRANCH_PUBLIC_IP)
        is_gps_ok = (distance <= MAX_DISTANCE_METERS)
        
        if not is_wifi_ok:
            st.error(f"⛔ تعذر التسجيل: أنت غير متصل بشبكة Wi-Fi الفرع! (IP الحالي: {user_ip})")
        elif not is_gps_ok:
            st.error(f"⛔ تعذر التسجيل: موقعك يبعد بـ {int(distance)}m عن الفرع. النطاق المسموح: {int(MAX_DISTANCE_METERS)}m")
        else:
            st.success("✅ تم التحقق من الموقع وشبكة الفرع بنجاح!")
            
            with st.form("attendance_form"):
                phone_input = st.text_input("أدخل رقم الموبايل المسجل:", max_chars=11)
                action_type = st.radio("نوع الحركة:", ["تسجيل حضور", "تسجيل انصراف"])
                
                submit_btn = st.form_submit_button("إرسال الحركة")
                
                if submit_btn:
                    phone_clean = phone_input.strip()
                    if phone_clean in EMPLOYEES:
                        emp_name = EMPLOYEES[phone_clean]
                        today_date = datetime.now().strftime("%Y-%m-%d")
                        now_time = datetime.now().strftime("%I:%M:%S %p")
                        
                        cursor.execute('''
                            INSERT INTO attendance_logs (phone, emp_name, date, time, action, ip_address, distance_m)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (phone_clean, emp_name, today_date, now_time, action_type, user_ip, distance))
                        conn.commit()
                        
                        st.balloons()
                        st.success(f"تم {action_type} بنجاح للموظف: **{emp_name}** في تمام الساعة {now_time}")
                    else:
                        st.error("❌ رقم الموبايل غير مسجل ضمن قائمة موظفي الفرع!")
    else:
        st.warning("⏳ جاري جلب الموقع والشبكة... يرجى السماح بالوصول للـ GPS.")

elif page == "لوحة تحكم الإدارة":
    if os.path.exists(LOGO_PATH):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(LOGO_PATH, width=200)
            
    st.title(f"🔒 لوحة الإدارة - {PROJECT_NAME}")
    
    pwd = st.text_input("أدخل كلمة مرور المدير:", type="password")
    
    if pwd == ADMIN_PASSWORD:
        st.success("تم تسجيل الدخول بنجاح.")
        
        df = pd.read_sql_query("SELECT * FROM attendance_logs ORDER BY id DESC", conn)
        
        st.subheader("سجلات الحضور")
        st.dataframe(df, use_container_width=True)
        
        import io
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Employee_Attendance')
            
        st.download_button(
            label="📥 تحميل التقرير الشامل (Excel)",
            data=buffer.getvalue(),
            file_name=f"Employee_Attendance_Report_{datetime.now().strftime('%Y_%m_%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    elif pwd != "":
        st.error("كلمة المرور غير صحيحة!")
