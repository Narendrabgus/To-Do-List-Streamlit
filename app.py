import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import io
import xlsxwriter
from datetime import datetime, date

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Log Aktivitas", layout="wide", page_icon="📝")

# --- SLOT WAKTU OTOMATIS ---
TIME_SLOTS = [
    "08.00 - 10.00",
    "10.00 - 12.00",
    "13.00 - 15.00",
    "15.00 - 17.00"
]

# --- 2. CSS CUSTOM ---
st.markdown("""
    <style>
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0);
        color: white !important;
    }
    [data-testid="stDecoration"] { display: none; }
    [data-testid="stHeader"] button { color: white !important; }
    [data-testid="stHeader"] svg { fill: white !important; }

    .stApp { background-color: #0033cc; }
    .block-container { padding-top: 3rem; padding-bottom: 2rem; }

    h1, h2, h3, h4, h5, p, div, span, li { color: #000000 !important; }

    .stButton button {
        padding: 0.2rem 0.5rem !important;
        font-size: 0.8rem !important;
        width: 100%;
    }

    .table-header {
        font-weight: bold;
        background-color: #9bc2e6;
        padding: 10px;
        border: 1px solid #000;
        text-align: center;
        color: #000;
        margin-bottom: 5px;
    }

    .activity-row {
        border-bottom: 1px dashed #ccc;
        padding-bottom: 10px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. HELPER FUNCTIONS ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def format_indo(tgl_str):
    try:
        if isinstance(tgl_str, str):
            tgl_obj = datetime.strptime(tgl_str, '%Y-%m-%d').date()
        else:
            tgl_obj = tgl_str
        hari_dict = {
            'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu',
            'Thursday': 'Kamis', 'Friday': 'Jumat',
            'Saturday': 'Sabtu', 'Sunday': 'Minggu'
        }
        bulan_dict = {
            1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
            5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
            9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
        }
        return f"{hari_dict[tgl_obj.strftime('%A')]}, {tgl_obj.day} {bulan_dict[tgl_obj.month]} {tgl_obj.year}"
    except:
        return tgl_str

def count_activity_per_day(conn, user, tanggal):
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM logs WHERE user=? AND tanggal=?", (user, tanggal))
    return c.fetchone()[0]

def generate_excel(df):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Laporan')

    header_fmt = workbook.add_format({
        'bold': True, 'font_color': '#000000',
        'bg_color': '#9bc2e6', 'border': 1,
        'align': 'center', 'valign': 'vcenter'
    })

    body_fmt = workbook.add_format({
        'text_wrap': True, 'border': 1,
        'valign': 'top', 'align': 'left'
    })

    center_fmt = workbook.add_format({
        'text_wrap': True, 'border': 1,
        'valign': 'top', 'align': 'center'
    })

    headers = ['ID', 'Tanggal', 'Waktu', 'Uraian Kegiatan', 'Hasil']
    for col, h in enumerate(headers):
        worksheet.write(0, col, h, header_fmt)

    for row, data in enumerate(df.values):
        worksheet.write(row+1, 0, data[0], center_fmt)
        worksheet.write(row+1, 1, str(data[1]), center_fmt)
        worksheet.write(row+1, 2, data[2], center_fmt)
        worksheet.write(row+1, 3, data[3], body_fmt)
        worksheet.write(row+1, 4, data[4], body_fmt)

    worksheet.set_column('A:A', 5)
    worksheet.set_column('B:B', 25)
    worksheet.set_column('C:C', 15)
    worksheet.set_column('D:D', 50)
    worksheet.set_column('E:E', 30)

    workbook.close()
    return output.getvalue()

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('kegiatan.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            tanggal DATE,
            waktu TEXT,
            aktivitas TEXT,
            hasil TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    ''')
    conn.commit()
    return conn

def create_user(conn, username, password):
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password) VALUES (?,?)', (username, password))
        conn.commit()
        return True
    except:
        return False

def login_user(conn, username):
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    return c.fetchone()

def add_data(conn, user, tanggal, waktu, aktivitas, hasil):
    c = conn.cursor()
    c.execute('INSERT INTO logs (user, tanggal, waktu, aktivitas, hasil) VALUES (?, ?, ?, ?, ?)',
              (user, tanggal, waktu, aktivitas, hasil))
    conn.commit()

def update_data(conn, id, tanggal, waktu, aktivitas, hasil):
    c = conn.cursor()
    c.execute('UPDATE logs SET tanggal=?, waktu=?, aktivitas=?, hasil=? WHERE id=?',
              (tanggal, waktu, aktivitas, hasil, id))
    conn.commit()

def delete_data(conn, id):
    c = conn.cursor()
    c.execute('DELETE FROM logs WHERE id=?', (id,))
    conn.commit()

def view_data_filtered(conn, user, start_date, end_date):
    c = conn.cursor()
    query = '''
        SELECT id, tanggal, waktu, aktivitas, hasil
        FROM logs
        WHERE user = ? AND tanggal BETWEEN ? AND ?
        ORDER BY tanggal DESC, waktu ASC
    '''
    c.execute(query, (user, start_date, end_date))
    return c.fetchall()

# --- SESSION ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''
if 'edit_mode' not in st.session_state:
    st.session_state['edit_mode'] = False
if 'data_to_edit' not in st.session_state:
    st.session_state['data_to_edit'] = None

conn = init_db()

# ================= LOGIN =================
if not st.session_state['logged_in']:
    st.title("🔐 Login Sistem")
    u_in = st.text_input("Username")
    p_in = st.text_input("Password", type='password')

    if st.button("Masuk"):
        user_data = login_user(conn, u_in)
        if user_data and user_data[1] == make_hashes(p_in):
            st.session_state['logged_in'] = True
            st.session_state['username'] = u_in
            st.rerun()
        else:
            st.error("Login Gagal.")

# ================= MAIN =================
else:
    st.sidebar.title(f"Halo, {st.session_state['username']}")
    if st.sidebar.button("Log Out"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ''
        st.rerun()

    menu = ["Input Aktivitas", "Laporan & Filter"]
    choice = st.sidebar.radio("Navigasi", menu)

    # ===== INPUT =====
    if choice == "Input Aktivitas":
        st.title("📝 Input Aktivitas")

        with st.form("input_form"):
            tgl = st.date_input("Tanggal *", datetime.now())
            akt = st.text_area("Uraian Kegiatan *")
            hsl = st.text_area("Hasil / Output *")

            if st.form_submit_button("Simpan"):
                if akt and hsl:
                    curr = st.session_state['username']
                    count = count_activity_per_day(conn, curr, tgl)

                    if count < len(TIME_SLOTS):
                        auto_waktu = TIME_SLOTS[count]
                        add_data(conn, curr, tgl, auto_waktu, akt, hsl)
                        st.success("Tersimpan!")
                        st.rerun()
                    else:
                        st.error("Slot waktu hari ini sudah penuh (4 aktivitas).")
                else:
                    st.error("Lengkapi data.")

    # ===== LAPORAN =====
    elif choice == "Laporan & Filter":
        st.title("📊 Laporan Harian")

        c1, c2 = st.columns(2)
        with c1:
            start_d = st.date_input("Dari", date(2025, 1, 1))
        with c2:
            end_d = st.date_input("Sampai", datetime.now())

        raw_data = view_data_filtered(conn,
                                      st.session_state['username'],
                                      start_d, end_d)

        df_export = pd.DataFrame(raw_data,
                                 columns=['ID', 'Tanggal', 'Waktu', 'Uraian', 'Hasil'])

        if not df_export.empty:
            df_export['Tanggal'] = df_export['Tanggal'].apply(format_indo)
            excel_data = generate_excel(df_export)

            st.download_button(
                label="📥 Download Laporan (Excel .xlsx)",
                data=excel_data,
                file_name=f"Laporan_{st.session_state['username']}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.dataframe(df_export)
        else:
            st.info("Belum ada data.")
