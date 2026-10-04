import io
from datetime import date
import pandas as pd
import streamlit as st
from pathlib import Path
from streamlit_js_eval import streamlit_js_eval

from database import *
from utils import distance_meters, valid_coords, token

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="منظومة حضور وانصراف العاملين",
    page_icon="logo.png",
    layout="centered",
    initial_sidebar_state="expanded"
)
init_db()

# 2. التنسيق البرمجي: توسيط العناصر، الاتجاه من اليمين لليسار، وبطاقات الدخول
st.markdown("""

""", unsafe_allow_html=True)

# 3. جلب بصمة الجهاز المخصصة
device_id = streamlit_js_eval(
    js_expressions="""
    (function() {
        let id = localStorage.getItem('emp_device_id');
        if (!id) {
            id = 'DEV-' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
            localStorage.setItem('emp_device_id', id);
        }
        return id;
    })()
    """,
    key="get_device_id"
)

# 4. إدارة الجلسة
branch_name = get_setting("branch_name", "الأكاديمية المهنية للمعلمين")

def is_admin():
    return st.session_state.get("admin", False)

if "admin" not in st.session_state:
    st.session_state.admin = False

# 5. عرض الشعار والعناوين في المنتصف
logo_path = Path(__file__).resolve().parent / "logo.png"
if logo_path.exists():
    st.image(str(logo_path), width=120)

st.title("منظومة حضور وانصراف العاملين")
st.subheader(f"{branch_name} – فرع الجيزة")
st.caption("نظام رقمي لإدارة حضور وانصراف موظفي الفرع")
st.divider()

# 6. القائمة الجانبية جهة اليمين
with st.sidebar:
    st.markdown("### ☰ القائمة")
    pages = ["تسجيل الحضور والانصراف", "QR Code"]
    if is_admin():
        pages += ["لوحة الإدارة", "الموظفون", "التقارير", "إعدادات الفرع"]
        if st.button("تسجيل خروج الإدارة", use_container_width=True):
            st.session_state.admin = False
            st.rerun()
    else:
        pages += ["دخول الإدارة"]
    page = st.radio("", pages)

# 7. محتوى الصفحات
if page == "تسجيل الحضور والانصراف":
    st.subheader("📍 تسجيل الحضور والانصراف")
    token_from_url = st.query_params.get("site", "")
    configured_token = get_setting("site_token", "")
    if not token_from_url:
        st.warning("يجب فتح هذه الصفحة من خلال QR Code الخاص بالفرع.")
    elif not configured_token or token_from_url != configured_token:
        st.error("رمز QR غير صالح.")
        st.stop()

    action = st.radio("العملية", ["حضور", "انصراف"], horizontal=True)
    code = st.text_input("كود الموظف", placeholder="أدخل اسم المستخدم / الكود")
    
    if st.button("📍 التحقق من الموقع وتسجيل العملية", type="primary", use_container_width=True):
        code = normalize_code(code)
        if not code:
            st.error("أدخل كود الموظف."); st.stop()
            
        employee = get_employee(code, active_only=True)
        if not employee:
            st.error("كود الموظف غير صحيح أو الموظف غير نشط."); st.stop()

        if not device_id:
            st.error("تعذر التعرف على بصمة الجهاز، يرجى إعادة تحديث الصفحة."); st.stop()

        device_ok, device_msg = verify_employee_device(code, device_id)
        if not device_ok:
            st.error(device_msg); st.stop()

        lat = get_setting("branch_latitude", "")
        lon = get_setting("branch_longitude", "")
        radius = float(get_setting("radius_m", "100") or 100)
        if not valid_coords(lat, lon):
            st.error("لم يتم ضبط إحداثيات الفرع بعد. ادخل إلى إعدادات الفرع من الإدارة."); st.stop()

        try:
            from streamlit_js_eval import get_geolocation
            loc = get_geolocation(component_key="attendance_location")
        except Exception as e:
            st.error(f"تعذر تشغيل GPS: {e}"); st.stop()
        if not loc:
            st.info("اسمح للمتصفح باستخدام الموقع ثم اضغط الزر مرة أخرى."); st.stop()
        if "error" in loc:
            st.error(loc["error"].get("message", "تعذر الحصول على الموقع.")); st.stop()
            
        coords = loc.get("coords", {})
        user_lat, user_lon = coords.get("latitude"), coords.get("longitude")
        accuracy = coords.get("accuracy")
        if user_lat is None or user_lon is None:
            st.error("بيانات الموقع غير مكتملة."); st.stop()

        dist = distance_meters(float(user_lat), float(user_lon), float(lat), float(lon))
        st.info(f"المسافة عن الفرع: {dist:.1f} متر")
        if dist > radius:
            st.error(f"لم يتم التسجيل: الجهاز خارج نطاق الفرع المحدد ({radius:.0f} متر)."); st.stop()

        today = today_records(code)
        if action == "حضور" and any(x["action"] == "حضور" for x in today):
            st.warning("تم تسجيل حضور هذا الموظف اليوم بالفعل."); st.stop()
        if action == "انصراف":
            if not any(x["action"] == "حضور" for x in today):
                st.warning("لا يمكن تسجيل الانصراف قبل تسجيل الحضور."); st.stop()
            if any(x["action"] == "انصراف" for x in today):
                st.warning("تم تسجيل الانصراف لهذا الموظف اليوم بالفعل."); st.stop()

        record_attendance(employee, action, user_lat, user_lon, dist, accuracy)
        st.success(f"تم تسجيل {action} بنجاح للموظف: {employee['name']}")

    if code:
        rows = today_records(code)
        if rows:
            st.markdown("### سجل اليوم")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

elif page == "دخول الإدارة":
    st.subheader("🔑 تسجيل الدخول للإدارة")
    password = st.text_input("كلمة المرور", type="password", placeholder="أدخل كلمة مرور الإدارة")
    if st.button("دخول ➔", use_container_width=True):
        if password == get_setting("admin_password", "123456"):
            st.session_state.admin = True
            st.rerun()
        else:
            st.error("كلمة المرور غير صحيحة.")

elif page == "QR Code":
    st.subheader("🔳 QR Code الخاص بالفرع")
    site_token = get_setting("site_token", "")
    if not site_token:
        st.info("يجب على الإدارة إنشاء QR أولًا من إعدادات الفرع.")
    else:
        try:
            import qrcode
            base = st.context.url.split("?")[0]
            url = f"{base}?site={site_token}&action=حضور"
            img = qrcode.make(url)
            buf = io.BytesIO(); img.save(buf, format="PNG")
            data = buf.getvalue()
            st.image(data, width=280)
            st.download_button("📥 تحميل QR", data, "giza_attendance_qr.png", "image/png", use_container_width=True)
        except Exception as e:
            st.error(f"تعذر إنشاء QR: {e}")

elif page == "لوحة الإدارة":
    st.subheader("📊 لوحة الإدارة")
    s = stats_today()
    a, b, c, d = st.columns(4)
    a.metric("إجمالي الموظفين", s["total"])
    b.metric("الموظفون النشطون", s["active"])
    c.metric("حضور اليوم", s["present"])
    d.metric("انصراف اليوم", s["departed"])

elif page == "الموظفون":
    st.subheader("👥 إدارة الموظفين")
    with st.expander("➕ إضافة موظف جديد", expanded=True):
        with st.form("add_employee"):
            c1, c2 = st.columns(2)
            code = c1.text_input("كود الموظف *", placeholder="001")
            name = c2.text_input("اسم الموظف *")
            job = c1.text_input("الوظيفة")
            phone = c2.text_input("الهاتف")
            submit = st.form_submit_button("💾 إضافة الموظف", type="primary", use_container_width=True)
        if submit:
            ok, msg = add_employee(code, name, job, phone)
            if ok: st.success(msg); st.rerun()
            else: st.error(msg)

    employees = list_employees()
    if employees:
        df = pd.DataFrame(employees)
        df["الحالة"] = df["active"].map({1: "نشط", 0: "غير نشط"})
        df["ربط الهاتف"] = df["device_id"].apply(lambda x: "مسجل" if x else "غير مسجل")
        st.dataframe(df[["employee_code", "name", "job_title", "phone", "الحالة", "ربط الهاتف"]].rename(columns={"employee_code": "كود الموظف", "name": "اسم الموظف", "job_title": "الوظيفة", "phone": "الهاتف"}), use_container_width=True, hide_index=True)

        st.markdown("### ✏️ تعديل / تفعيل / فك ربط الهاتف / حذف")
        selected = st.selectbox("اختر الموظف", [f"{e['employee_code']} — {e['name']}" for e in employees])
        selected_code = selected.split(" — ", 1)[0]
        emp = get_employee(selected_code) or get_employee(selected_code, active_only=False)
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("الاسم", value=emp["name"], key="edit_name")
            new_job = st.text_input("الوظيفة", value=emp["job_title"], key="edit_job")
        with c2:
            new_phone = st.text_input("الهاتف", value=emp["phone"], key="edit_phone")
            st.write(f"الكود: **{emp['employee_code']}**")
        
        x1, x2, x3, x4 = st.columns(4)
        if x1.button("حفظ التعديل", use_container_width=True):
            if update_employee(selected_code, new_name, new_job, new_phone): st.success("تم الحفظ."); st.rerun()
        if x2.button("تفعيل/تعطيل", use_container_width=True):
            set_employee_active(selected_code, not bool(emp["active"])); st.success("تم تغيير حالة الموظف."); st.rerun()
        if x3.button("🔄 فك ربط الهاتف", use_container_width=True):
            register_employee_device(selected_code, None)
            st.success("تم فك ربط الهاتف القديم.")
            st.rerun()
        if x4.button("حذف الموظف", use_container_width=True):
            delete_employee(selected_code); st.success("تم حذف الموظف."); st.rerun()

elif page == "التقارير":
    st.subheader("📑 التقارير")
    c1, c2 = st.columns(2)
    start = c1.date_input("من", value=date.today())
    end = c2.date_input("إلى", value=date.today())
    code_filter = st.text_input("كود موظف (اختياري)")
    rows = attendance_report(start, end, code_filter or None)
    if not rows: st.info("لا توجد بيانات للفترة المحددة.")
    else:
        df = pd.DataFrame(rows); st.dataframe(df, use_container_width=True, hide_index=True)
        x = io.BytesIO()
        with pd.ExcelWriter(x, engine="openpyxl") as writer: df.to_excel(writer, index=False, sheet_name="الحضور والانصراف")
        st.download_button("📥 تنزيل Excel", x.getvalue(), "attendance_report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

elif page == "إعدادات الفرع":
    st.subheader("⚙️ إعدادات الفرع")
    name = st.text_input("اسم الفرع", value=get_setting("branch_name"))
    lat = st.text_input("خط العرض", value=get_setting("branch_latitude"))
    lon = st.text_input("خط الطول", value=get_setting("branch_longitude"))
    radius = st.number_input("نطاق الحضور بالمتر", 10, 1000, int(float(get_setting("radius_m", "100") or 100)))
    new_password = st.text_input("كلمة مرور الإدارة الجديدة", type="password")
    if st.button("💾 حفظ الإعدادات", type="primary", use_container_width=True):
        if not valid_coords(lat, lon): st.error("أدخل إحداثيات صحيحة.")
        else:
            set_setting("branch_name", name); set_setting("branch_latitude", lat); set_setting("branch_longitude", lon); set_setting("radius_m", radius)
            if new_password: set_setting("admin_password", new_password)
            st.success("تم حفظ الإعدادات."); st.rerun()
    st.divider()
    st.subheader("🔑 QR Code")
    if st.button("إنشاء / تغيير QR", use_container_width=True):
        set_setting("site_token", token()); st.success("تم إنشاء QR جديد."); st.rerun()

# 8. البطاقات السفلي والتذييل
st.divider()
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.success("🛡️ **أمان البيانات**\n\nحماية وخصوصية عالية")
with col2:
    st.info("⏱️ **دقة في التسجيل**\n\nوقت الحضور والانصراف")
with col3:
    st.warning("📍 **تحديد الموقع**\n\nضمن نطاق الفرع")
with col4:
    st.error("👥 **إدارة فعالة**\n\nلمواردنا البشرية")

st.caption("— تصميم وتنفيذ أحمد الجنزوري (مدير الفرع) —")
