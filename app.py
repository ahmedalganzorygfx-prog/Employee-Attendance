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
# 4. تحميل كاشف الوجوه الصارم
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
# 5. الدوال البرمجية وفحص الوجه الصارم
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
    except Exception:
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

def analyze_liveness_photo(image_bytes):
    """فحص صارم: يرفض التوقيع نهائياً إذا لم يظهر وجه بشري واضح أمام الكاميرا"""
    try:
        # قراءة محتوى الصورة من الذاكرة
        image_bytes.seek(0)
        file_bytes = np.frombuffer(image_bytes.read(), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        if img is None:
            return False, "تعذر قراءة الصورة! يرجى التقاط الصورة مجدداً."

        # التأكد من تحميل الكاشف
        if not os.path.exists(FACE_CASCADE_PATH):
            download_cascade_if_missing(
                FACE_CASCADE_PATH, 
                "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
            )

        face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # كشف أبعاد الوجوه البشرية بالصورة
        faces = face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(80, 80)
        )
        
        if len(faces) == 0:
            return False, "❌ لم يتم الكشف عن وجه بشري! يرجى النظر والتصوير أمام الكاميرا مباشرة."
        elif len(faces) > 1:
            return False, "❌ تم كشف أكثر من وجه بالصورة! يرجى إظهار وجه الموظف فقط."
            
        return True, "تم الكشف عن الوجه بنجاح"
    except Exception as e:
        return False, f"❌ حدث خطأ أثناء تحليل الوجه: يرجى التقاط صورة سيلفي جديدة واضحة."

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
    st.info("📸 شرط التوقيع: يلتزم الموظف بالنظر مباشرة للكاميرا وإظهار وجهه بوضوح.")
    
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
            
            st.subheader("📸 التقاط صورة سيلفي مباشرة لتأكيد التوقيع:")
            camera_photo = st.camera_input("انقر التقاط صورة شخصية لوجهك")
            
            if st.button("تأكيد وتوثيق التوقيع", type="primary"):
                code_clean = emp_code_input.strip()
                
                if not code_clean:
                    st.warning("⚠️ يرجى إدخال كود الموظف.")
                elif camera_photo is None:
                    st.warning("⚠️ يرجى التقاط صورة سيلفي حية عبر الكاميرا لتأكيد التوقيع.")
                elif code_clean in active_employees:
                    # فحص الوجه الصارم
                    is_valid, check_msg = analyze_liveness_photo(camera_photo)
                    
                    if not is_valid:
                        st.error(check_msg)
                    else:
                        emp_info = active_employees[code_clean]
                        emp_name = emp_info["name"]
                        
                        now_egypt = get_egypt_datetime()
                        today_date = now_egypt.strftime("%Y-%m-%d")
                        now_time = now_egypt.strftime("%I:%M:%S %p")
                        timestamp_str = now_egypt.strftime("%Y%m%d_%H%M%S")
                        
                        photo_filename = f"{code_clean}_{timestamp_str}.png"
                        photo_filepath = os.path.join(UPLOADS_DIR, photo_filename)
                        
                        camera_photo.seek(0)
                        with open(photo_filepath, "wb") as f:
                            f.write(camera_photo.getbuffer())
                        
                        cursor.execute('''
                            INSERT INTO attendance_logs (emp_code, emp_name, date, time, action, ip_address, distance_m, photo_path)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (code_clean, emp_name, today_date, now_time, action_type, user_ip, distance, photo_filepath))
                        conn.commit()
                        
                        st.balloons()
                        st.success(f"📸 تم فحص الوجه وتوثيق {action_type} بنجاح للموظف: **{emp_name}** (الكود: {code_clean}) في تمام الساعة {now_time}")
                else:
                    st.error("❌ كود الموظف غير صحيح أو غير مفعل ضمن قائمة الفرع!")
    else:
        st.warning("⏳ جاري جلب الموقع والشبكة... يرجى السماح بالوصول للـ GPS والكاميرا.")

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

        tab1, tab2, tab3 = st.tabs(["📊 سجلات الحضور والصور", "👥 إدارة الموظفين والأكواد", "⚙ إعدادات النظام والـ QR"])
        
        # ----------------- سجلات الحضور والصور -----------------
        with tab1:
            st.subheader("سجلات الحضور والتوقيعات الموثقة بالصور")
            
            try:
                df_logs = pd.read_sql_query("SELECT id, emp_code AS 'كود الموظف', emp_name AS 'اسم الموظف', date AS 'التاريخ', time AS 'الوقت', action AS 'الحركة', ip_address AS 'عنوان IP', distance_m AS 'المسافة (متر)', photo_path FROM attendance_logs ORDER BY id DESC", conn)
            except Exception:
                df_logs = pd.DataFrame()
                
            if not df_logs.empty:
                for idx, row in df_logs.iterrows():
                    with st.container():
                        col_text, col_img = st.columns([3, 1])
                        with col_text:
                            st.markdown(f"### 👤 {row['اسم الموظف']} (الكود: {row['كود الموظف']})")
                            st.write(f"📌 **الحركة:** {row['الحركة']} | 📅 **التاريخ:** {row['التاريخ']} | ⏰ **الوقت:** {row['الوقت']}")
                            dist_val = int(row['المسافة (متر)']) if pd.notnull(row['المسافة (متر)']) else 0
                            st.write(f"🌐 **IP الشبكة:** {row['عنوان IP']} | 📍 **المسافة عن الفرع:** {dist_val} متر")
                        with col_img:
                            p_path = row['photo_path']
                            if isinstance(p_path, str) and p_path and os.path.exists(p_path):
                                st.image(p_path, caption="صورة التوقيع", width=130)
                            else:
                                st.caption("لا توجد صورة")
                        st.markdown("---")
            else:
                st.info("لا توجد سجلات حضور مسجلة حتى الآن.")
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_logs.to_excel(writer, index=False, sheet_name='Employee_Attendance')
                
            now_eg = get_egypt_datetime()
            st.download_button(
                label="📥 تحميل التقرير الشامل (Excel)",
                data=buffer.getvalue(),
                file_name=f"Attendance_Report_{now_eg.strftime('%Y_%m_%d')}.xlsx",
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
                        edit_phone = st.text_input("تحديث رقم الموبايل:", value=emp_data['رقم الموبايل'])
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

        # ----------------- إعدادات النظام والـ QR -----------------
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
