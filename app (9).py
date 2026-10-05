import streamlit as st
import sqlite3
import base64
from pathlib import Path
from datetime import date, datetime


# ============================================================
# إعدادات الصفحة
# ============================================================

st.set_page_config(
    page_title="منظومة الوارد والصادر",
    page_icon="📁",
    layout="centered",
    initial_sidebar_state="collapsed"
)


# ============================================================
# المسارات
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "documents.db"

ARCHIVE_DIR = BASE_DIR / "Archive_Files"
INCOMING_DIR = ARCHIVE_DIR / "Incoming"
OUTGOING_DIR = ARCHIVE_DIR / "Outgoing"

LOGO_PATH = BASE_DIR / "logo.png"

INCOMING_DIR.mkdir(parents=True, exist_ok=True)
OUTGOING_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# إعدادات النظام
# ============================================================

APP_PASSWORD = "1234"


# ============================================================
# دالة تحويل الصورة إلى Base64
# ============================================================

def get_image_base64(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except Exception:
        return None


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    html,
    body {
        margin: 0 !important;
        padding: 0 !important;
    }

    .stApp {
        margin: 0 !important;
        padding: 0 !important;
        direction: rtl;
        text-align: right;
        background-color: #f7f9fc;
    }

    .block-container {
        max-width: 900px !important;
        width: 94% !important;
        padding-top: 10px !important;
        padding-bottom: 25px !important;
        margin: 0 auto !important;
    }

    header,
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    #MainMenu,
    footer {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }

    .login-container {
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;
        text-align: center;
        padding-top: 10px;
        padding-bottom: 20px;
        margin: 0 auto;
    }

    .login-logo-container {
        width: 100%;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        text-align: center !important;
        margin: 0 auto 12px auto !important;
        padding: 0 !important;
    }

    .login-logo-container img {
        display: block !important;
        width: 180px !important;
        height: 180px !important;
        object-fit: contain;
        margin-left: auto !important;
        margin-right: auto !important;
        position: relative !important;
        left: auto !important;
        right: auto !important;
    }

    .login-main-title {
        width: 100%;
        text-align: center !important;
        color: #17365d;
        font-size: 32px;
        font-weight: 900;
        line-height: 1.5;
        margin: 0 auto 4px auto;
    }

    .login-sub-title {
        width: 100%;
        text-align: center !important;
        color: #294d7c;
        font-size: 21px;
        font-weight: 700;
        line-height: 1.5;
        margin: 0 auto 18px auto;
    }

    .login-box {
        width: 100%;
        max-width: 430px;
        margin: 0 auto;
        text-align: right;
    }

    .internal-logo-container {
        width: 100%;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        text-align: center !important;
        margin: 0 auto 8px auto !important;
        padding: 0 !important;
    }

    .internal-logo-container img {
        display: block !important;
        width: 145px !important;
        height: 145px !important;
        object-fit: contain;
        margin-left: auto !important;
        margin-right: auto !important;
        position: relative !important;
        left: auto !important;
        right: auto !important;
    }

    .main-title {
        width: 100%;
        text-align: center !important;
        color: #17365d;
        font-size: 27px;
        font-weight: 900;
        line-height: 1.5;
        margin: 0 auto 3px auto;
    }

    .sub-title {
        width: 100%;
        text-align: center !important;
        color: #294d7c;
        font-size: 19px;
        font-weight: 600;
        line-height: 1.5;
        margin: 0 auto 18px auto;
    }

    .section-title {
        background: linear-gradient(
            90deg,
            #17365d,
            #294d7c
        );
        color: white;
        border-radius: 10px;
        padding: 10px 15px;
        margin-top: 12px;
        margin-bottom: 10px;
        font-size: 20px;
        font-weight: 800;
        text-align: right;
    }

    .info-card {
        background: white;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 12px;
        box-shadow:
            0 2px 8px rgba(0, 0, 0, 0.08);
        border: 1px solid #e5eaf0;

        direction: rtl !important;
        text-align: right !important;
    }

    .record-title {
        color: #17365d;
        font-size: 18px;
        font-weight: 800;
        margin-bottom: 8px;
        direction: rtl;
        text-align: right;
    }

    .record-line {
        font-size: 15px;
        color: #333;
        margin: 4px 0;
        line-height: 1.7;
        direction: rtl;
        text-align: right;
    }

    .custom-footer {
        width: 100%;
        text-align: center;
        color: #6b7280;
        font-size: 13px;
        margin-top: 25px;
        padding-top: 10px;
        border-top: 1px solid #e5e7eb;
    }

    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea {
        direction: rtl;
        text-align: right;
    }

    div[data-testid="stDateInput"] input {
        direction: rtl;
        text-align: right;
    }

    .stButton > button {
        width: 100%;
        border-radius: 8px;
        min-height: 42px;
        font-weight: 700;
    }

    section[data-testid="stFileUploader"] {
        direction: rtl;
        text-align: right;
    }

    div[data-testid="stExpander"] {
        border-radius: 10px !important;
        border: 1px solid #e1e7ef !important;
        background: white !important;
        margin-bottom: 10px !important;

        direction: rtl !important;
        text-align: right !important;
    }

    div[data-testid="stExpander"] > details {
        direction: rtl !important;
        text-align: right !important;
    }

    div[data-testid="stExpander"] summary {
        direction: rtl !important;
        text-align: right !important;
    }

    div[data-testid="stExpander"] summary p {
        direction: rtl !important;
        text-align: right !important;
    }

    div[data-testid="stAlert"] {
        direction: rtl;
        text-align: right;
    }

    div[data-baseweb="select"] {
        direction: rtl;
    }

    @media (max-width: 600px) {

        .block-container {
            width: 94% !important;
            padding-top: 5px !important;
        }

        .login-container {
            padding-top: 5px;
        }

        .login-logo-container img {
            width: 135px !important;
            height: 135px !important;
        }

        .login-main-title {
            font-size: 23px;
        }

        .login-sub-title {
            font-size: 17px;
        }

        .internal-logo-container img {
            width: 110px !important;
            height: 110px !important;
        }

        .main-title {
            font-size: 21px;
        }

        .sub-title {
            font-size: 16px;
        }

        .section-title {
            font-size: 17px;
        }

    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# Session State
# ============================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "page" not in st.session_state:
    st.session_state.page = "الرئيسية"

if "search_query" not in st.session_state:
    st.session_state.search_query = ""


# ============================================================
# شاشة تسجيل الدخول
# ============================================================

if not st.session_state.authenticated:

    logo_base64 = None

    if LOGO_PATH.exists():
        logo_base64 = get_image_base64(LOGO_PATH)

    st.markdown(
        '<div class="login-container">',
        unsafe_allow_html=True
    )

    if logo_base64:

        st.markdown(
            f"""
            <div class="login-logo-container">
                <img
                    src="data:image/png;base64,{logo_base64}"
                    alt="شعار الأكاديمية"
                >
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            """
            <div style="
                font-size:80px;
                text-align:center;
                width:100%;
                margin-bottom:10px;
            ">
                📁
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        """
        <div class="login-main-title">
            الأكاديمية المهنية للمعلمين – فرع الجيزة
        </div>

        <div class="login-sub-title">
            المنظومة الرقمية للوارد والصادر
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="login-box">',
        unsafe_allow_html=True
    )

    with st.form(key="login_form"):

        password = st.text_input(
            "🔐 كلمة المرور",
            type="password",
            placeholder="أدخل كلمة المرور"
        )

        login_clicked = st.form_submit_button(
            "🔓 تسجيل الدخول",
            type="primary"
        )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

    if login_clicked:

        if password == APP_PASSWORD:

            st.session_state.authenticated = True

            st.rerun()

        else:

            st.error("❌ كلمة المرور غير صحيحة")

    st.markdown(
        """
        <div class="custom-footer">
            ✦ تصميم وتنفيذ أحمد الجنزوري - مدير الفرع ✦
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

    st.stop()


# ============================================================
# قاعدة البيانات
# ============================================================

def get_connection():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            doc_type TEXT NOT NULL,

            doc_number TEXT NOT NULL,

            doc_date TEXT NOT NULL,

            party TEXT NOT NULL,

            subject TEXT NOT NULL,

            file_path TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()

    conn.close()


init_db()


# ============================================================
# الترقيم التلقائي للمستندات
# ============================================================

def get_next_document_number(doc_type):

    conn = get_connection()

    row = conn.execute(
        """
        SELECT MAX(CAST(doc_number AS INTEGER))
        FROM documents
        WHERE doc_type = ?
        """,
        (doc_type,)
    ).fetchone()

    conn.close()

    max_number = row[0]

    if doc_type == "وارد":

        start_number = 961

    else:

        start_number = 1160

    if max_number is None or max_number < start_number:

        return str(start_number)

    return str(max_number + 1)


# ============================================================
# وظائف مساعدة
# ============================================================

def get_archive_folder(doc_type):

    if doc_type == "وارد":

        return INCOMING_DIR

    return OUTGOING_DIR


def save_uploaded_file(uploaded_file, doc_type):

    if uploaded_file is None:

        return None

    folder = get_archive_folder(doc_type)

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    original_name = Path(uploaded_file.name).name

    safe_name = f"{timestamp}_{original_name}"

    file_path = folder / safe_name

    with open(file_path, "wb") as file:

        file.write(
            uploaded_file.getbuffer()
        )

    return str(file_path)


def get_documents(
    doc_type=None,
    search_text=None
):

    conn = get_connection()

    query = """
        SELECT *
        FROM documents
        WHERE 1=1
    """

    params = []

    if doc_type and doc_type != "الكل":

        query += """
            AND doc_type = ?
        """

        params.append(doc_type)

    if search_text:

        query += """
            AND (
                doc_number LIKE ?
                OR party LIKE ?
                OR subject LIKE ?
                OR doc_date LIKE ?
            )
        """

        search_value = f"%{search_text}%"

        params.extend(
            [
                search_value,
                search_value,
                search_value,
                search_value
            ]
        )

    query += """
        ORDER BY id DESC
    """

    rows = conn.execute(
        query,
        params
    ).fetchall()

    conn.close()

    return rows


def get_document(document_id):

    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM documents
        WHERE id = ?
        """,
        (document_id,)
    ).fetchone()

    conn.close()

    return row


def delete_document(document_id):

    conn = get_connection()

    row = conn.execute(
        """
        SELECT file_path
        FROM documents
        WHERE id = ?
        """,
        (document_id,)
    ).fetchone()

    if row:

        file_path = row["file_path"]

        if file_path:

            try:

                path = Path(file_path).resolve()

                archive_root = ARCHIVE_DIR.resolve()

                if archive_root in path.parents and path.exists():

                    path.unlink()

            except Exception:
                pass

    conn.execute(
        """
        DELETE FROM documents
        WHERE id = ?
        """,
        (document_id,)
    )

    conn.commit()

    conn.close()


def update_document(
    document_id,
    doc_number,
    doc_date,
    party,
    subject,
    new_file_path=None
):

    conn = get_connection()

    if new_file_path:

        conn.execute(
            """
            UPDATE documents
            SET
                doc_number = ?,
                doc_date = ?,
                party = ?,
                subject = ?,
                file_path = ?
            WHERE id = ?
            """,
            (
                doc_number,
                doc_date,
                party,
                subject,
                new_file_path,
                document_id
            )
        )

    else:

        conn.execute(
            """
            UPDATE documents
            SET
                doc_number = ?,
                doc_date = ?,
                party = ?,
                subject = ?
            WHERE id = ?
            """,
            (
                doc_number,
                doc_date,
                party,
                subject,
                document_id
            )
        )

    conn.commit()

    conn.close()


def delete_old_file(file_path):

    if not file_path:

        return

    try:

        path = Path(file_path).resolve()

        archive_root = ARCHIVE_DIR.resolve()

        if archive_root in path.parents and path.exists():

            path.unlink()

    except Exception:

        pass


def go_to(page):

    st.session_state.page = page

    st.rerun()


# ============================================================
# رأس البرنامج الداخلي
# ============================================================

if LOGO_PATH.exists():

    logo_base64 = get_image_base64(LOGO_PATH)

    if logo_base64:

        st.markdown(
            f"""
            <div class="internal-logo-container">
                <img
                    src="data:image/png;base64,{logo_base64}"
                    alt="شعار الأكاديمية"
                >
            </div>
            """,
            unsafe_allow_html=True
        )

else:

    st.warning(
        "⚠️ لم يتم العثور على ملف logo.png"
    )


st.markdown(
    """
    <div class="main-title">
        الأكاديمية المهنية للمعلمين – فرع الجيزة
    </div>

    <div class="sub-title">
        المنظومة الرقمية للوارد والصادر
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# الصفحة الرئيسية
# ============================================================

if st.session_state.page == "الرئيسية":

    st.markdown(
        """
        <div class="section-title">
            📥 سجل الوارد
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "➕ إضافة وارد جديد",
            key="add_incoming_home"
        ):

            go_to("إضافة وارد")

    with col2:

        if st.button(
            "📋 عرض الوارد",
            key="view_incoming_home"
        ):

            st.session_state.view_filter = "وارد"

            go_to("السجلات")


    st.markdown(
        """
        <div class="section-title">
            📤 سجل الصادر
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "➕ إضافة صادر جديد",
            key="add_outgoing_home"
        ):

            go_to("إضافة صادر")

    with col2:

        if st.button(
            "📋 عرض الصادر",
            key="view_outgoing_home"
        ):

            st.session_state.view_filter = "صادر"

            go_to("السجلات")


    st.markdown(
        """
        <div class="section-title">
            🔎 البحث في الأرشيف
        </div>
        """,
        unsafe_allow_html=True
    )

    search_text = st.text_input(
        "ابحث برقم المستند أو الجهة أو الموضوع أو التاريخ",
        value="",
        placeholder="اكتب كلمة البحث هنا..."
    )

    if st.button(
        "🔎 تنفيذ البحث",
        type="primary",
        key="search_home"
    ):

        st.session_state.search_query = search_text

        go_to("البحث")


# ============================================================
# إضافة وارد / صادر
# ============================================================

elif st.session_state.page in [
    "إضافة وارد",
    "إضافة صادر"
]:

    doc_type = (
        "وارد"
        if st.session_state.page == "إضافة وارد"
        else "صادر"
    )

    title_icon = "📥" if doc_type == "وارد" else "📤"

    st.markdown(
        f"""
        <div class="section-title">
            {title_icon} إضافة مستند {doc_type} جديد
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.form(
        key=f"add_form_{doc_type}"
    ):

        # ====================================================
        # الرقم التلقائي
        # ====================================================

        doc_number = get_next_document_number(doc_type)

        st.text_input(
            "رقم المستند",
            value=doc_number,
            disabled=True
        )

        doc_date = st.date_input(
            "تاريخ المستند *",
            value=date.today(),
            format="DD/MM/YYYY"
        )

        party = st.text_input(
            "الجهة / الطرف *",
            placeholder="أدخل اسم الجهة"
        )

        subject = st.text_area(
            "موضوع المستند *",
            placeholder="أدخل موضوع المستند",
            height=100
        )

        uploaded_file = st.file_uploader(
            "إرفاق ملف PDF",
            type=["pdf"],
            help="يمكنك اختيار ملف PDF لأرشفته مع المستند."
        )

        col1, col2 = st.columns(2)

        with col1:

            save_clicked = st.form_submit_button(
                "💾 حفظ المستند",
                type="primary"
            )

        with col2:

            cancel_clicked = st.form_submit_button(
                "↩️ إلغاء"
            )


    if cancel_clicked:

        go_to("الرئيسية")


    if save_clicked:

        errors = []

        if not doc_number.strip():

            errors.append(
                "رقم المستند مطلوب."
            )

        if not party.strip():

            errors.append(
                "الجهة / الطرف مطلوب."
            )

        if not subject.strip():

            errors.append(
                "موضوع المستند مطلوب."
            )


        if errors:

            for error in errors:

                st.error(
                    f"❌ {error}"
                )

        else:

            try:

                file_path = save_uploaded_file(
                    uploaded_file,
                    doc_type
                )

                conn = get_connection()

                conn.execute(
                    """
                    INSERT INTO documents (
                        doc_type,
                        doc_number,
                        doc_date,
                        party,
                        subject,
                        file_path
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_type,
                        doc_number.strip(),
                        doc_date.strftime("%d/%m/%Y"),
                        party.strip(),
                        subject.strip(),
                        file_path
                    )
                )

                conn.commit()

                conn.close()

                st.success(
                    f"✅ تم حفظ المستند {doc_type} بنجاح."
                )

                st.session_state.page = "الرئيسية"

                st.rerun()

            except Exception as e:

                st.error(
                    f"❌ حدث خطأ أثناء الحفظ: {e}"
                )


# ============================================================
# عرض السجلات
# ============================================================

elif st.session_state.page == "السجلات":

    st.markdown(
        """
        <div class="section-title">
            📋 سجلات الوارد والصادر
        </div>
        """,
        unsafe_allow_html=True
    )

    default_filter = st.session_state.get(
        "view_filter",
        "الكل"
    )

    filter_options = [
        "الكل",
        "وارد",
        "صادر"
    ]

    if default_filter not in filter_options:

        default_filter = "الكل"

    selected_filter = st.selectbox(
        "نوع السجل",
        filter_options,
        index=filter_options.index(
            default_filter
        )
    )

    rows = get_documents(
        doc_type=selected_filter
    )

    st.write(
        f"📊 عدد السجلات: **{len(rows)}**"
    )


    if not rows:

        st.info(
            "لا توجد سجلات متاحة."
        )

    else:

        for row in rows:

            icon = (
                "📥"
                if row["doc_type"] == "وارد"
                else "📤"
            )

            expander_title = (
                f"{icon} "
                f"{row['doc_type']} - "
                f"{row['doc_number']} - "
                f"{row['subject']}"
            )

            with st.expander(
                expander_title
            ):

                st.markdown(
                    f"""
                    <div class="info-card">

                        <div class="record-title">
                            📥 بيانات المستند
                        </div>

                        <div class="record-line">
                            <b>النوع:</b> وارد
                        </div>

                        <div class="record-line">
                            <b>رقم المستند:</b> 122
                        </div>

                        <div class="record-line">
                            <b>التاريخ:</b> 29/09/2026
                        </div>

                        <div class="record-line">
                            <b>الجهة:</b> الاكاديمية
                        </div>

                        <div class="record-line">
                            <b>الموضوع:</b> اعادة تعيين
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True
                )


                if row["file_path"]:

                    file_path = Path(
                        row["file_path"]
                    )

                    if file_path.exists():

                        with open(
                            file_path,
                            "rb"
                        ) as pdf_file:

                            st.download_button(
                                "📥 تحميل ملف PDF",
                                data=pdf_file.read(),
                                file_name=file_path.name,
                                mime="application/pdf",
                                key=f"download_{row['id']}"
                            )

                    else:

                        st.warning(
                            "⚠️ الملف المرفق غير موجود في الأرشيف."
                        )

                else:

                    st.info(
                        "📄 لا يوجد ملف PDF مرفق."
                    )


                col1, col2 = st.columns(2)

                with col1:

                    if st.button(
                        "✏️ تعديل",
                        key=f"edit_{row['id']}"
                    ):

                        st.session_state.edit_id = row["id"]

                        go_to("تعديل")


                with col2:

                    if st.button(
                        "🗑️ حذف",
                        key=f"delete_{row['id']}"
                    ):

                        st.session_state.delete_id = row["id"]

                        go_to("تأكيد الحذف")


    if st.button(
        "🏠 العودة للرئيسية",
        key="back_from_records"
    ):

        go_to("الرئيسية")


# ============================================================
# البحث
# ============================================================

elif st.session_state.page == "البحث":

    st.markdown(
        """
        <div class="section-title">
            🔎 البحث في الأرشيف
        </div>
        """,
        unsafe_allow_html=True
    )

    search_text = st.text_input(
        "كلمة البحث",
        value=st.session_state.search_query,
        placeholder="رقم المستند / الجهة / الموضوع / التاريخ"
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "🔎 بحث",
            type="primary",
            key="search_again"
        ):

            st.session_state.search_query = search_text

            st.rerun()


    with col2:

        if st.button(
            "🏠 الرئيسية",
            key="back_search"
        ):

            go_to("الرئيسية")


    if st.session_state.search_query:

        rows = get_documents(
            search_text=st.session_state.search_query
        )

        st.markdown(
            f"""
            <div class="section-title">
                📊 نتائج البحث
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write(
            f"عدد النتائج: **{len(rows)}**"
        )


        if not rows:

            st.warning(
                "لم يتم العثور على نتائج مطابقة."
            )

        else:

            for row in rows:

                icon = (
                    "📥"
                    if row["doc_type"] == "وارد"
                    else "📤"
                )

                title = (
                    f"{icon} "
                    f"{row['doc_type']} - "
                    f"{row['doc_number']} - "
                    f"{row['subject']}"
                )

                with st.expander(title):

                    st.markdown(
                        f"""
                        <div class="info-card">

                            <div class="record-line">
                                <b>النوع:</b>
                                {row["doc_type"]}
                            </div>

                            <div class="record-line">
                                <b>رقم المستند:</b>
                                {row["doc_number"]}
                            </div>

                            <div class="record-line">
                                <b>التاريخ:</b>
                                {row["doc_date"]}
                            </div>

                            <div class="record-line">
                                <b>الجهة:</b>
                                {row["party"]}
                            </div>

                            <div class="record-line">
                                <b>الموضوع:</b>
                                {row["subject"]}
                            </div>

                        </div>
                        """,
                        unsafe_allow_html=True
                    )


                    if row["file_path"]:

                        file_path = Path(
                            row["file_path"]
                        )

                        if file_path.exists():

                            with open(
                                file_path,
                                "rb"
                            ) as pdf_file:

                                st.download_button(
                                    "📥 تحميل PDF",
                                    data=pdf_file.read(),
                                    file_name=file_path.name,
                                    mime="application/pdf",
                                    key=f"search_download_{row['id']}"
                                )


# ============================================================
# تعديل مستند
# ============================================================

elif st.session_state.page == "تعديل":

    document_id = st.session_state.get(
        "edit_id"
    )

    if not document_id:

        st.error(
            "❌ لم يتم تحديد المستند."
        )

        if st.button(
            "🏠 الرئيسية"
        ):

            go_to("الرئيسية")

    else:

        row = get_document(
            document_id
        )

        if not row:

            st.error(
                "❌ المستند غير موجود."
            )

            if st.button(
                "🏠 الرئيسية"
            ):

                go_to("الرئيسية")

        else:

            st.markdown(
                f"""
                <div class="section-title">
                    ✏️ تعديل مستند {row["doc_type"]}
                </div>
                """,
                unsafe_allow_html=True
            )


            with st.form(
                key=f"edit_form_{document_id}"
            ):

                doc_number = st.text_input(
                    "رقم المستند *",
                    value=row["doc_number"]
                )

                try:

                    old_date = datetime.strptime(
                        row["doc_date"],
                        "%d/%m/%Y"
                    ).date()

                except Exception:

                    old_date = date.today()


                doc_date = st.date_input(
                    "تاريخ المستند *",
                    value=old_date,
                    format="DD/MM/YYYY"
                )

                party = st.text_input(
                    "الجهة / الطرف *",
                    value=row["party"]
                )

                subject = st.text_area(
                    "موضوع المستند *",
                    value=row["subject"],
                    height=100
                )

                st.write(
                    "📎 الملف الحالي:"
                )

                if row["file_path"]:

                    old_file = Path(
                        row["file_path"]
                    )

                    if old_file.exists():

                        st.info(
                            old_file.name
                        )

                    else:

                        st.warning(
                            "الملف الحالي غير موجود."
                        )

                else:

                    st.info(
                        "لا يوجد ملف مرفق حاليًا."
                    )


                new_file = st.file_uploader(
                    "استبدال ملف PDF",
                    type=["pdf"],
                    key=f"new_pdf_{document_id}"
                )


                col1, col2 = st.columns(2)

                with col1:

                    save_edit = st.form_submit_button(
                        "💾 حفظ التعديلات",
                        type="primary"
                    )

                with col2:

                    cancel_edit = st.form_submit_button(
                        "↩️ إلغاء"
                    )


            if cancel_edit:

                go_to("السجلات")


            if save_edit:

                errors = []

                if not doc_number.strip():

                    errors.append(
                        "رقم المستند مطلوب."
                    )

                if not party.strip():

                    errors.append(
                        "الجهة / الطرف مطلوبة."
                    )

                if not subject.strip():

                    errors.append(
                        "موضوع المستند مطلوب."
                    )


                if errors:

                    for error in errors:

                        st.error(
                            f"❌ {error}"
                        )

                else:

                    try:

                        new_file_path = None

                        old_file_path = row["file_path"]


                        if new_file:

                            new_file_path = save_uploaded_file(
                                new_file,
                                row["doc_type"]
                            )


                        update_document(
                            document_id=document_id,
                            doc_number=doc_number.strip(),
                            doc_date=doc_date.strftime(
                                "%d/%m/%Y"
                            ),
                            party=party.strip(),
                            subject=subject.strip(),
                            new_file_path=new_file_path
                        )


                        if new_file_path and old_file_path:

                            delete_old_file(
                                old_file_path
                            )


                        st.success(
                            "✅ تم تحديث المستند بنجاح."
                        )

                        st.session_state.page = "السجلات"

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"❌ حدث خطأ أثناء التعديل: {e}"
                        )


# ============================================================
# تأكيد الحذف
# ============================================================

elif st.session_state.page == "تأكيد الحذف":

    document_id = st.session_state.get(
        "delete_id"
    )

    row = get_document(
        document_id
    ) if document_id else None


    st.markdown(
        """
        <div class="section-title">
            🗑️ حذف المستند
        </div>
        """,
        unsafe_allow_html=True
    )


    if not row:

        st.error(
            "❌ المستند غير موجود."
        )

        if st.button(
            "🏠 الرئيسية"
        ):

            go_to("الرئيسية")

    else:

        st.warning(
            f"""
            ⚠️ هل أنت متأكد من حذف المستند؟

            **النوع:** {row["doc_type"]}

            **رقم المستند:** {row["doc_number"]}

            **الجهة:** {row["party"]}

            **الموضوع:** {row["subject"]}

            سيتم حذف السجل والملف المرفق إن وجد.
            """
        )


        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "🗑️ نعم، حذف المستند",
                type="primary"
            ):

                try:

                    delete_document(
                        document_id
                    )

                    st.success(
                        "✅ تم حذف المستند بنجاح."
                    )

                    st.session_state.page = "السجلات"

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"❌ حدث خطأ أثناء الحذف: {e}"
                    )


        with col2:

            if st.button(
                "↩️ إلغاء"
            ):

                go_to("السجلات")


# ============================================================
# الفوتر
# ============================================================

st.markdown(
    """
    <div class="custom-footer">
        الأكاديمية المهنية للمعلمين - فرع الجيزة
        <br>
        ✦ تصميم وتنفيذ أحمد الجنزوري - مدير الفرع ✦
    </div>
    """,
    unsafe_allow_html=True
)
