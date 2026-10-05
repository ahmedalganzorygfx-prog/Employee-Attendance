import streamlit as st
import sqlite3
import pandas as pd
import math
import requests
from datetime import datetime
import pytz
from streamlit_js_eval import get_geolocation, get_user_agent
import os
import qrcode
import io

# ==========================================
# 1. الإعدادات العامة للشعار والبرنامج
# ==========================================
PROJECT_NAME = "حضور وانصراف العاملين بفرع الجيزة"
LOGO_PATH = "logo.png"

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
        phone TEXT,
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
        device_id TEXT,
        is_active INTEGER DEFAULT 1
    )
''')

try:
    cursor.execute("ALTER TABLE employees ADD COLUMN device_id TEXT")
    conn.commit()
except sqlite3.OperationalError:
    pass

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

def get_active_employees_map():
    try:
        cursor.execute("SELECT emp_code, emp_name, phone, device_id FROM employees WHERE is_active = 1")
        rows = cursor.fetchall()
        emp_dict = {}
        for code, name, phone, dev_id in rows:
            emp_dict[str(code).strip()] = {
                "name": str(name).strip(),
                "phone": str(phone).strip() if phone else "",
                "device_id": str(dev_id).strip() if dev_id else None
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
                device_id TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        sample_employees = [
            ('101', 'أحمد حسني الجنزوري', '01069996245', 'مدير الفرع', None),
            ('102', 'خالد عبدالحكيم هارون', '01120807631', 'عضو IT', None),
            ('103', 'أحمد محمد عمر', '01201109892', 'عضو تنمية مهنية', None)
        ]
        cursor.executemany("INSERT OR REPLACE INTO employees VALUES (?, ?, ?, ?, ?, 1)", sample_employees)
        conn.commit()
        
        cursor.execute("SELECT emp_code, emp_name, phone, device_id FROM employees WHERE is_active = 1")
        rows = cursor.fetchall()
        emp_dict = {}
        for code, name, phone, dev_id in rows:
            emp_dict[str(code).strip()] = {
                "name": str(name).strip(),
                "phone": str(phone).strip() if phone else "",
                "device_id": str(dev_id).strip() if dev_id else None
            }
        return emp_dict

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
    st.info("📱 أدخل كودك الخاص. يتم اقتران الهاتف بكود الموظف لمنع التوقيع بالنيابة.")
    
    branch_public_ip = get_setting("branch_ip")
    branch_lat = float(get_setting("branch_lat"))
    branch_lon = float(get_setting("branch_lon"))
    max_distance_meters = float(get_setting("max_distance"))
    disable_wifi_check = get_setting("disable_wifi_check") == "1"
    
    user_ip = get_user_ip()
    loc = get_geolocation()
    user_agent = get_user_agent()
    active_employees = get_active_employees_map()
    
    # توليد بصمة فريدة دقيقة بالهاتف والمتصفح
    current_device_id = None
    if user_agent:
        ua_clean = str(user_agent).strip()
        current_device_id = f"DEV_{abs(hash(ua_clean))}"

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
            
            with st.form("attendance_form", clear_on_submit=True):
                emp_code_input = st.text_input("أدخل كود الموظف المخصص لك:", placeholder="مثال: 101")
                action_type = st.radio("نوع الحركة:", ["تسجيل حضور", "تسجيل انصراف"])
                
                submit_btn = st.form_submit_button("تأكيد التوقيع")
                
                if submit_btn:
                    code_clean = emp_code_input.strip()
                    
                    if not code_clean:
                        st.warning("⚠️ يرجى إدخال كود الموظف.")
                    elif code_clean in active_employees:
                        emp_info = active_employees[code_clean]
                        emp_name = emp_info["name"]
                        registered_phone = emp_info["phone"]
                        registered_device = emp_info["device_id"]
                        
                        # 1. فحص إن كان هذا الهاتف مقترناً بزميل آخر
                        cursor.execute("SELECT emp_code, emp_name FROM employees WHERE device_id=? AND emp_code != ?", (current_device_id, code_clean))
                        other_bound_emp = cursor.fetchone()
                        
                        if other_bound_emp and current_device_id:
                            st.error(f"🚫 تعذر التسجيل: هذا الموبايل مقترن مسبقاً بالموظف ({other_bound_emp[1]}). لا يمكن التوقيع لزميل آخر من نفس الهاتف!")
                        # 2. ربط الهاتف لأول مرة للموظف
                        elif not registered_device and current_device_id:
                            cursor.execute("UPDATE employees SET device_id=? WHERE emp_code=?", (current_device_id, code_clean))
                            conn.commit()
                            
                            now_egypt = get_egypt_datetime()
                            today_date = now_egypt.strftime("%Y-%m-%d")
                            now_time = now_egypt.strftime("%I:%M:%S %p")
                            
                            cursor.execute('''
                                INSERT INTO attendance_logs (emp_code, emp_name, phone, date, time, action, ip_address, distance_m)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (code_clean, emp_name, registered_phone, today_date, now_time, action_type, user_ip, distance))
                            conn.commit()
                            
                            st.balloons()
                            st.success(f"📱 تم اقتران موبايلك بكودك وتسجيل {action_type} بنجاح للموظف: **{emp_name}** في تمام الساعة {now_time}")
                        # 3. التأكد من تطابق الهاتف المسجل
                        elif registered_device and registered_device != current_device_id:
                            st.error("❌ تعذر التسجيل: كود هذا الموظف مقترن بهاتف آخر! يرجى التوقيع من جهازك المسجل فقط.")
                        else:
                            now_egypt = get_egypt_datetime()
                            today_date = now_egypt.strftime("%Y-%m-%d")
                            now_time = now_egypt.strftime("%I:%M:%S %p")
                            
                            cursor.execute('''
                                INSERT INTO attendance_logs (emp_code, emp_name, phone, date, time, action, ip_address, distance_m)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (code_clean, emp_name, registered_phone, today_date, now_time, action_type, user_ip, distance))
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
                df_logs = pd.read_sql_query("SELECT id, emp_code AS 'كود الموظف', emp_name AS 'اسم الموظف', phone AS 'رقم الموبايل', date AS 'التاريخ', time AS 'الوقت', action AS 'الحركة', ip_address AS 'عنوان IP', distance_m AS 'المسافة (متر)' FROM attendance_logs ORDER BY id DESC", conn)
            except Exception:
                df_logs = pd.DataFrame()
                
            st.subheader("سجلات الحضور والتسجيلات")
            st.dataframe(df_logs, use_container_width=True)
            
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
            
            # زر إضافي لتنظيف واقتران كافة الأجهزة للتجربة من جديد
            if st.button("🧹 مسح اقتران جميع الأجهزة (تصفير الأجهزة المسجلة)", type="secondary"):
                cursor.execute("UPDATE employees SET device_id=NULL")
                conn.commit()
                st.success("تم مسح اقتران كافة الأجهزة! يمكن للجميع الاقتران مجدداً بكود كل موظف.")
                st.rerun()

            st.markdown("---")
            
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
                                cursor.execute("INSERT INTO employees (emp_code, emp_name, phone, job_title, device_id) VALUES (?, ?, ?, ?, NULL)",
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
                df_emp_all = pd.read_sql_query("SELECT emp_code AS 'كود الموظف', emp_name AS 'اسم الموظف', phone AS 'رقم الموبايل', job_title AS 'المسمى الوظيفي', device_id AS 'معرف الجهاز', is_active AS 'الحالة (1=مفعل)' FROM employees", conn)
            except Exception:
                df_emp_all = pd.DataFrame()
                
            st.dataframe(df_emp_all, use_container_width=True)
            
            with st.expander("🔓 إعادة فك اقتران جهاز موظف معين (عند تغيير الهاتف)"):
                if not df_emp_all.empty:
                    reset_code = st.selectbox("اختر كود الموظف لفك اقتران هاتفه القديم:", df_emp_all['كود الموظف'].tolist(), key="reset_device_select")
                    if st.button("إعادة ضبط اقتران الهاتف للموظف المحفوظ"):
                        cursor.execute("UPDATE employees SET device_id=NULL WHERE emp_code=?", (reset_code,))
                        conn.commit()
                        st.success(f"تم فك اقتران الهاتف للكود ({reset_code}) بنجاح!")
                        st.rerun()

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
