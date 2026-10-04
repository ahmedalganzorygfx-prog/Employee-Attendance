import streamlit as st
import sqlite3
import pandas as pd
import math
import requests
from datetime import datetime
from streamlit_js_eval import get_geolocation
import os
import qrcode
import io

# ==========================================
# 1. الإعدادات العامة للشعار والبرنامج
# ==========================================
PROJECT_NAME = "حضور وانصراف العاملين بفرع الجيزة"
LOGO_PATH = "logo.png"

ADMIN_PASSWORD = "admin_giza_2026"

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
# 3. قواعد البيانات وإدارة الإعدادات المصححة
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
        distance_m REAL
    )
''')

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

# الرابط الفعلي المباشر لتطبيقك
REAL_APP_URL = "https://employee-attendance-dv932asxnr57mmovkwpltp.streamlit.app/"

# الإعدادات الافتراضية
DEFAULT_SETTINGS = {
    "branch_ip": "41.38.200.191",
    "branch_lat": "30.2104",
    "branch_lon": "31.3681",
    "max_distance": "50.0",
    "disable_wifi_check": "0",
    "app_url": REAL_APP_URL
}

# إدخال الإعدادات الافتراضية فقط إذا لم تكن موجودة مسبقاً (INSERT OR IGNORE)
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
# 4. الدوال البرمجية المساعدة
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

def get_active_employees_by_code():
    try:
        df_emp = pd.read_sql_query("SELECT emp_code, emp_name FROM employees WHERE is_active = 1", conn)
        return dict(zip(df_emp['emp_code'], df_emp['emp_name']))
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
            ('101', 'أحمد حسني', '01012345671', 'مدير الفرع'),
            ('102', 'محمد علي', '01012345672', 'موظف'),
            ('103', 'محمود إبراهيم', '01012345673', 'موظف')
        ]
        cursor.executemany("INSERT OR REPLACE INTO employees VALUES (?, ?, ?, ?, 1)", sample_employees)
        conn.commit()
        
        df_emp = pd.read_sql_query("SELECT emp_code, emp_name FROM employees WHERE is_active = 1", conn)
        return dict(zip(df_emp['emp_code'], df_emp['emp_name']))

# ==========================================
# 5. الشاشات الرئيسية للتطبيق
# ==========================================
if page == "تسجيل الحضور/الانصراف":
    if os.path.exists(LOGO_PATH):
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.image(LOGO_PATH, width=280)
            
    st.title(PROJECT_NAME)
    st.caption("بوابة تسجيل الحضور والأنصراف الرقمية بالفرع")
    st.info("📲 ادخل كودك الخاص بشرط الاتصال بـ Wi-Fi الفرع وتفعيل موقع الـ GPS بالجوال.")
    
    branch_public_ip = get_setting("branch_ip")
    branch_lat = float(get_setting("branch_lat"))
    branch_lon = float(get_setting("branch_lon"))
    max_distance_meters = float(get_setting("max_distance"))
    disable_wifi_check = get_setting("disable_wifi_check") == "1"
    
    user_ip = get_user_ip()
    loc = get_geolocation()
    active_employees = get_active_employees_by_code()
    
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
            
            with st.form("attendance_form"):
                emp_code_input = st.text_input("أدخل كود الموظف المخصص لك:", placeholder="مثال: 101")
                action_type = st.radio("نوع الحركة:", ["تسجيل حضور", "تسجيل انصراف"])
                
                submit_btn = st.form_submit_button("تأكيد التوقيع")
                
                if submit_btn:
                    code_clean = emp_code_input.strip()
                    if code_clean in active_employees:
                        emp_name = active_employees[code_clean]
                        today_date = datetime.now().strftime("%Y-%m-%d")
                        now_time = datetime.now().strftime("%I:%M:%S %p")
                        
                        cursor.execute('''
                            INSERT INTO attendance_logs (emp_code, emp_name, date, time, action, ip_address, distance_m)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (code_clean, emp_name, today_date, now_time, action_type, user_ip, distance))
                        conn.commit()
                        
                        st.balloons()
                        st.success(f"تم {action_type} بنجاح للموظف: **{emp_name}** (الكود: {code_clean}) في تمام الساعة {now_time}")
                    else:
                        st.error("❌ كود الموظف غير صحيح أو غير مفعل ضمن قائمة الفرع!")
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

        tab1, tab2, tab3 = st.tabs(["📊 سجلات الحضور", "👥 إدارة الموظفين والأكواد", "⚙ إعدادات النظام والـ QR"])
        
        # ----------------- سجلات الحضور -----------------
        with tab1:
            try:
                df_logs = pd.read_sql_query("SELECT id, emp_code AS 'كود الموظف', emp_name AS 'اسم الموظف', date AS 'التاريخ', time AS 'الوقت', action AS 'الحركة', ip_address AS 'عنوان IP', distance_m AS 'المسافة (متر)' FROM attendance_logs ORDER BY id DESC", conn)
            except Exception:
                df_logs = pd.DataFrame()
                
            st.subheader("سجلات الحضور والتسجيلات")
            st.dataframe(df_logs, use_container_width=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_logs.to_excel(writer, index=False, sheet_name='Employee_Attendance')
                
            st.download_button(
                label="📥 تحميل التقرير الشامل (Excel)",
                data=buffer.getvalue(),
                file_name=f"Attendance_Report_{datetime.now().strftime('%Y_%m_%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        # ----------------- إدارة الموظفين والأكواد -----------------
        with tab2:
            st.subheader("إدارة الموظفين وأكواد التوقيع")
            
            if "new_code_val" not in st.session_state:
                st.session_state["new_code_val"] = ""
            if "new_name_val" not in st.session_state:
                st.session_state["new_name_val"] = ""
            if "new_phone_val" not in st.session_state:
                st.session_state["new_phone_val"] = ""
            if "new_job_val" not in st.session_state:
                st.session_state["new_job_val"] = "موظف"

            with st.expander("➕ إضافة موظف جديد وكود توقيع"):
                with st.form("add_emp_form"):
                    new_code = st.text_input("كود الموظف (مثال: 101):", value=st.session_state["new_code_val"])
                    new_name = st.text_input("اسم الموظف الثلاثي:", value=st.session_state["new_name_val"])
                    new_phone = st.text_input("رقم الموبايل (اختياري):", value=st.session_state["new_phone_val"], max_chars=11)
                    new_job = st.text_input("المسمى الوظيفي:", value=st.session_state["new_job_val"])
                    
                    add_btn = st.form_submit_button("حفظ الموظف والكود")
                    if add_btn:
                        if new_code.strip() and new_name.strip():
                            try:
                                cursor.execute("INSERT INTO employees (emp_code, emp_name, phone, job_title) VALUES (?, ?, ?, ?)",
                                               (new_code.strip(), new_name.strip(), new_phone.strip(), new_job.strip()))
                                conn.commit()
                                st.success(f"تمت إضافة الموظف {new_name} بالكود ({new_code}) بنجاح!")
                                
                                st.session_state["new_code_val"] = ""
                                st.session_state["new_name_val"] = ""
                                st.session_state["new_phone_val"] = ""
                                st.session_state["new_job_val"] = "موظف"
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("كود الموظف هذا مستخدم بالفعل لموظف آخر!")
                        else:
                            st.warning("يرجى إدخال كود الموظف والاسم الثلاثي.")
            
            try:
                df_emp_all = pd.read_sql_query("SELECT emp_code AS 'كود الموظف', emp_name AS 'اسم الموظف', phone AS 'رقم الموبايل', job_title AS 'المسمى الوظيفي', is_active AS 'الحالة (1=مفعل)' FROM employees", conn)
            except Exception:
                df_emp_all = pd.DataFrame()
                
            st.dataframe(df_emp_all, use_container_width=True)
            
            with st.expander("✏️ تعديل بيانات وكود موظف"):
                if not df_emp_all.empty:
                    selected_code = st.selectbox("اختر كود الموظف المراد تعديله:", df_emp_all['كود الموظف'].tolist())
                    emp_data = df_emp_all[df_emp_all['كود الموظف'] == selected_code].iloc[0]
                    
                    with st.form("edit_emp_form"):
                        edit_name = st.text_input("تحديث الاسم:", value=emp_data['اسم الموظف'])
                        edit_phone = st.text_input("تحديث الموبايل:", value=emp_data['رقم الموبايل'])
                        edit_job = st.text_input("تحديث المسمى الوظيفي:", value=emp_data['المسمى الوظيفي'])
                        edit_active = st.checkbox("حالة التفعيل (مسموح له بالتسجيل)", value=bool(emp_data['الحالة (1=مفعل)']))
                        
                        update_btn = st.form_submit_button("تحديث البيانات")
                        if update_btn:
                            cursor.execute("UPDATE employees SET emp_name=?, phone=?, job_title=?, is_active=? WHERE emp_code=?",
                                           (edit_name.strip(), edit_phone.strip(), edit_job.strip(), 1 if edit_active else 0, selected_code))
                            conn.commit()
                            st.success("تم تحديث بيانات الموظف بنجاح!")
                            st.rerun()
                            
            with st.expander("🗑️ حذف موظف"):
                if not df_emp_all.empty:
                    del_code = st.selectbox("اختر كود الموظف المراد حذفه نهائياً:", df_emp_all['كود الموظف'].tolist(), key="del_select")
                    
                    if st.button("حذف الموظف الآن", type="primary"):
                        cursor.execute("DELETE FROM employees WHERE emp_code=?", (del_code,))
                        conn.commit()
                        st.warning("تم حذف الموظف من قاعدة البيانات!")
                        st.rerun()

        # ----------------- إعدادات النظام والـ QR المصححة -----------------
        with tab3:
            st.subheader("⚙ تعديل إعدادات الـ IP والموقع الجغرافي (GPS)")
            
            current_ip = get_setting("branch_ip")
            current_lat = get_setting("branch_lat")
            current_lon = get_setting("branch_lon")
            current_dist = get_setting("max_distance")
            current_url = get_setting("app_url")
            current_disable = get_setting("disable_wifi_check") == "1"
            
            with st.form("settings_form"):
                new_ip = st.text_input("عنوان IP العام لراوتر Wi-Fi الفرع:", value=current_ip)
                
                col_lat, col_lon = st.columns(2)
                with col_lat:
                    new_lat = st.text_input("خط العرض (Latitude):", value=current_lat)
                with col_lon:
                    new_lon = st.text_input("خط الطول (Longitude):", value=current_lon)
                    
                new_dist = st.text_input("أقصى مسافة مسموحة بالـ GPS (بالأمتار):", value=current_dist)
                new_url = st.text_input("رابط التطبيق الخاص بالـ QR Code:", value=current_url)
                disable_wifi = st.checkbox("تعطيل فحص الـ Wi-Fi IP مؤقتاً (للتجربة من خارج الفرع)", value=current_disable)
                
                save_settings_btn = st.form_submit_button("حفظ الإعدادات الجديدة")
                
                if save_settings_btn:
                    set_setting("branch_ip", new_ip.strip())
                    set_setting("branch_lat", new_lat.strip())
                    set_setting("branch_lon", new_lon.strip())
                    set_setting("max_distance", new_dist.strip())
                    set_setting("app_url", new_url.strip())
                    set_setting("disable_wifi_check", "1" if disable_wifi else "0")
                    
                    st.success("✅ تم حفظ الإعدادات الجديدة بنجاح وتحديث الـ QR Code!")
                    st.rerun()

            st.markdown("---")
            st.subheader("📱 رمز QR الموحد للفرع (جاهز للطباعة)")
            
            # جلب الرابط الحالي والمحدث بدقة
            active_qr_url = get_setting("app_url")
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=3
            )
            qr.add_data(active_qr_url)
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="#10233F", back_color="white")
            
            qr_buf = io.BytesIO()
            img_qr.save(qr_buf, format="PNG")
            
            col_qr1, col_qr2 = st.columns([1, 2])
            with col_qr1:
                st.image(qr_buf.getvalue(), caption="رمز QR للفرع", width=220)
            with col_qr2:
                st.write(f"الرابط المضمّن في الـ QR حالياً:\n`{active_qr_url}`")
                st.download_button(
                    label="📥 تحميل صورة الـ QR للطباعة",
                    data=qr_buf.getvalue(),
                    file_name="Branch_Attendance_QR.png",
                    mime="image/png"
                )
