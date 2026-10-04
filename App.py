import streamlit as st
import sqlite3
import pandas as pd
import math
import requests
from datetime import datetime
from streamlit_js_eval import get_geolocation
import os

# ==========================================
# 1. الإعدادات العامة للعنوان والشعار
# ==========================================
PROJECT_NAME = "حضور وانصراف العاملين بفرع الجيزة"
LOGO_PATH = "logo.png"

# إحداثيات موقع الفرع (قم بتحديثها طبقاً لموقعك الفعلي)
BRANCH_LAT = 30.0444
BRANCH_LON = 31.2357
MAX_DISTANCE_METERS = 50.0

# الـ Public IP المحدث لشبكة Wi-Fi الفرع
BRANCH_PUBLIC_IP = "34.190.100.134"

# كلمة مرور الإدارة
ADMIN_PASSWORD = "admin_giza_2026"

# ==========================================
# 2. تهيئة الواجهة ودعم اتجاه اليمين إلى اليسار (RTL)
# ==========================================
st.set_page_config(page_title=PROJECT_NAME, page_icon="🏢", layout="centered")

st.markdown("""
    
""", unsafe_allow_html=True)

st.sidebar.title(PROJECT_NAME)
page = st.sidebar.radio("الانتقال إلى:", ["تسجيل الحضور/الانصراف", "لوحة تحكم الإدارة"])

# ==========================================
# 3. الدوال البرمجية وقواعد البيانات
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

cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        phone TEXT PRIMARY KEY,
        emp_name TEXT NOT NULL,
        job_title TEXT DEFAULT 'موظف',
        is_active INTEGER DEFAULT 1
    )
''')
conn.commit()

def get_active_employees():
    df_emp = pd.read_sql_query("SELECT phone, emp_name FROM employees WHERE is_active = 1", conn)
    return dict(zip(df_emp['phone'], df_emp['emp_name']))

# ==========================================
# 4. الشاشات الرئيسية
# ==========================================
if page == "تسجيل الحضور/الانصراف":
    if os.path.exists(LOGO_PATH):
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.image(LOGO_PATH, width=280)
            
    st.title(PROJECT_NAME)
    st.caption("بوابة تسجيل الحضور والأنصراف الرقمية بالفرع")
    st.info("📲 يرجى الاتصال بـ Wi-Fi الفرع وتفعيل موقع الـ GPS بالجوال.")
    
    user_ip = get_user_ip()
    loc = get_geolocation()
    
    active_employees = get_active_employees()
    
    if loc and 'coords' in loc and user_ip:
        user_lat = loc['coords']['latitude']
        user_lon = loc['coords']['longitude']
        distance = calculate_distance(BRANCH_LAT, BRANCH_LON, user_lat, user_lon)
        
        # المطابقة مع الـ IP الجديد
        is_wifi_ok = (user_ip == BRANCH_PUBLIC_IP)
        is_gps_ok = (distance <= MAX_DISTANCE_METERS)
        
        if not is_wifi_ok:
            st.error(f"⛔ تعذر التسجيل: أنت غير متصل بشبكة Wi-Fi الفرع! (عنوان IP الحالي: {user_ip})")
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
                    if phone_clean in active_employees:
                        emp_name = active_employees[phone_clean]
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
                        st.error("❌ رقم الموبايل غير مسجل أو غير مفعل ضمن قائمة موظفي الفرع!")
    else:
        st.warning("⏳ جاري جلب الموقع والشبكة... يرجى السماح بالوصول للـ GPS.")

elif page == "لوحة تحكم الإدارة":
    if os.path.exists(LOGO_PATH):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(LOGO_PATH, width=200)
            
    st.title(f"🔒 لوحة الإدارة - {PROJECT_NAME}")
    
    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        with st.form("login_form"):
            pwd = st.text_input("أدخل كلمة مرور المدير:", type="password")
            login_btn = st.form_submit_button("دخول")
            
            if login_btn:
                if pwd == ADMIN_PASSWORD:
                    st.session_state["admin_logged_in"] = True
                    st.success("تم تسجيل الدخول بنجاح.")
                    st.rerun()
                else:
                    st.error("كلمة المرور غير صحيحة!")
    else:
        if st.button("🚪 تسجيل الخروج"):
            st.session_state["admin_logged_in"] = False
            st.rerun()

        tab1, tab2 = st.tabs(["📊 سجلات الحضور", "👥 إدارة الموظفين بالفرع"])
        
        with tab1:
            df_logs = pd.read_sql_query("SELECT * FROM attendance_logs ORDER BY id DESC", conn)
            st.subheader("سجلات الحضور والتسجيلات")
            st.dataframe(df_logs, use_container_width=True)
            
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_logs.to_excel(writer, index=False, sheet_name='Employee_Attendance')
                
            st.download_button(
                label="📥 تحميل التقرير الشامل (Excel)",
                data=buffer.getvalue(),
                file_name=f"Attendance_Report_{datetime.now().strftime('%Y_%m_%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        with tab2:
            st.subheader("إدارة قائمة الموظفين بالفرع")
            
            if "new_phone_val" not in st.session_state:
                st.session_state["new_phone_val"] = ""
            if "new_name_val" not in st.session_state:
                st.session_state["new_name_val"] = ""
            if "new_job_val" not in st.session_state:
                st.session_state["new_job_val"] = "موظف"

            with st.expander("➕ إضافة موظف جديد"):
                with st.form("add_emp_form"):
                    new_phone = st.text_input("رقم الموبايل (مثال: 01012345671):", value=st.session_state["new_phone_val"], max_chars=11)
                    new_name = st.text_input("اسم الموظف الثلاثي:", value=st.session_state["new_name_val"])
                    new_job = st.text_input("المسمى الوظيفي:", value=st.session_state["new_job_val"])
                    
                    add_btn = st.form_submit_button("حفظ الموظف")
                    if add_btn:
                        if new_phone.strip() and new_name.strip():
                            try:
                                cursor.execute("INSERT INTO employees (phone, emp_name, job_title) VALUES (?, ?, ?)",
                                               (new_phone.strip(), new_name.strip(), new_job.strip()))
                                conn.commit()
                                st.success(f"تمت إضافة الموظف {new_name} بنجاح!")
                                
                                st.session_state["new_phone_val"] = ""
                                st.session_state["new_name_val"] = ""
                                st.session_state["new_job_val"] = "موظف"
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("رقم الموبايل هذا مسجل بالفعل لموظف آخر!")
                        else:
                            st.warning("يرجى إدخال كافة البيانات المطلوبة.")
            
            df_emp_all = pd.read_sql_query("SELECT phone AS 'رقم الموبايل', emp_name AS 'اسم الموظف', job_title AS 'المسمى الوظيفي', is_active AS 'الحالة (1=مفعل)' FROM employees", conn)
            st.dataframe(df_emp_all, use_container_width=True)
            
            with st.expander("✏️ تعديل بيانات موظف"):
                if not df_emp_all.empty:
                    selected_phone = st.selectbox("اختر رقم الموظف المراد تعديله:", df_emp_all['رقم الموبايل'].tolist())
                    emp_data = df_emp_all[df_emp_all['رقم الموبايل'] == selected_phone].iloc[0]
                    
                    with st.form("edit_emp_form"):
                        edit_name = st.text_input("تحديث الاسم:", value=emp_data['اسم الموظف'])
                        edit_job = st.text_input("تحديث المسمى الوظيفي:", value=emp_data['المسمى الوظيفي'])
                        edit_active = st.checkbox("حالة التفعيل (مسموح له بالتسجيل)", value=bool(emp_data['الحالة (1=مفعل)']))
                        
                        update_btn = st.form_submit_button("تحديث البيانات")
                        if update_btn:
                            cursor.execute("UPDATE employees SET emp_name=?, job_title=?, is_active=? WHERE phone=?",
                                           (edit_name.strip(), edit_job.strip(), 1 if edit_active else 0, selected_phone))
                            conn.commit()
                            st.success("تم تحديث بيانات الموظف بنجاح!")
                            st.rerun()
                            
            with st.expander("🗑️ حذف موظف"):
                if not df_emp_all.empty:
                    del_phone = st.selectbox("اختر الموظف المراد حذفه نهائياً:", df_emp_all['رقم الموبايل'].tolist(), key="del_select")
                    
                    if st.button("حذف الموظف الآن", type="primary"):
                        cursor.execute("DELETE FROM employees WHERE phone=?", (del_phone,))
                        conn.commit()
                        st.warning("تم حذف الموظف من قاعدة البيانات!")
                        st.rerun()
