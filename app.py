import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime, date

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Log Aktivitas", layout="wide", page_icon="📝")

# --- 2. CSS CUSTOM (FIXED BLUE THEME & HIDE HEADER) ---
st.markdown("""
    <style>
    /* 1. SEMBUNYIKAN HEADER BAWAAN STREAMLIT (Kotak Putih Atas) */
    [data-testid="stHeader"] {
        display: none;
    }
    
    /* 2. BACKGROUND UTAMA (Kunci ke Biru) */
    .stApp {
        background-color: #0033cc;
    }
    
    /* 3. MENGURANGI JARAK ATAS (Padding) */
    .block-container {
        padding-top: 1rem; /* Jarak minimal dari atas */
        padding-bottom: 2rem;
    }

    /* 5. WARNA TEKS & LABEL (Kunci ke Hitam/Abu) */
    h1, h2, h3, h4, h5, p, div, span, li {
        color: #000000 !important;
    }
    label, .stDateInput label, .stSelectbox label, .stTextArea label, .stTextInput label {
        color: #333333 !important;
        font-weight: bold;
    }
    input, textarea, select {
        color: #333333;
    }

    /* 6. CSS KHUSUS TABEL LAPORAN (HTML) */
    .report-table {
        width: 100%;
        border-collapse: collapse;
        font-family: Arial, sans-serif;
        font-size: 14px;
        color: #000;
    }
    .report-table th {
        background-color: #9bc2e6; /* Header Biru Muda */
        border: 1px solid #000000;
        padding: 10px;
        text-align: center;
        font-weight: bold;
        color: #000000 !important;
    }
    .report-table td {
        border: 1px solid #000000;
        padding: 8px;
        vertical-align: top;
        background-color: #ffffff;
        color: #000000 !important;
    }
    /* Item dalam sel */
    .cell-item {
        margin-bottom: 8px;
        border-bottom: 1px dashed #ddd;
        padding-bottom: 4px;
    }
    .cell-item:last-child {
        border-bottom: none;
    }
    
    /* Garis pemisah manual */
    hr {
        border-top: 2px solid #cccccc !important; 
        opacity: 1;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. HELPER FUNCTIONS ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def format_indo(tgl_str):
    try:
        if isinstance(tgl_str, str): tgl_obj = datetime.strptime(tgl_str, '%Y-%m-%d').date()
        else: tgl_obj = tgl_str
        hari_dict = {'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu', 'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'}
        bulan_dict = {1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'}
        return f"{hari_dict[tgl_obj.strftime('%A')]}, {tgl_obj.day} {bulan_dict[tgl_obj.month]} {tgl_obj.year}"
    except: return tgl_str

# --- 4. DATABASE FUNCTION ---
def init_db():
    conn = sqlite3.connect('kegiatan.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, tanggal DATE, waktu TEXT, aktivitas TEXT, hasil TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
    conn.commit()
    return conn

def create_user(conn, username, password):
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password) VALUES (?,?)', (username, password))
        conn.commit()
        return True
    except: return False 

def login_user(conn, username, password):
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    return c.fetchall()

# CRUD
def add_data(conn, user, tanggal, waktu, aktivitas, hasil):
    c = conn.cursor()
    c.execute('INSERT INTO logs (user, tanggal, waktu, aktivitas, hasil) VALUES (?, ?, ?, ?, ?)', (user, tanggal, waktu, aktivitas, hasil))
    conn.commit()

def update_data(conn, id, tanggal, waktu, aktivitas, hasil):
    c = conn.cursor()
    c.execute('UPDATE logs SET tanggal=?, waktu=?, aktivitas=?, hasil=? WHERE id=?', (tanggal, waktu, aktivitas, hasil, id))
    conn.commit()

def delete_data(conn, id):
    c = conn.cursor()
    c.execute('DELETE FROM logs WHERE id=?', (id,))
    conn.commit()

def view_data_filtered(conn, user, start_date, end_date):
    c = conn.cursor()
    query = "SELECT id, tanggal, waktu, aktivitas, hasil FROM logs WHERE user = ? AND tanggal BETWEEN ? AND ? ORDER BY tanggal DESC, waktu ASC"
    c.execute(query, (user, start_date, end_date))
    return c.fetchall()

def seed_users(conn):
    default_users = ["Elisa Luhulima", "Ahmad Sobirin", "Dewi Puspita Sari", "Anni Samudra Wulan", "Nafi Alrasyid", "Muhamad Ichsan Kamil", "Oscar Gideon", "Rafael Yolens Putera Larung", "Izzat Nabela Ali", "Katrin Dian Lestari", "Diah", "Gary", "Rika"]
    default_pass = make_hashes("123456") 
    c = conn.cursor()
    for user in default_users:
        c.execute('SELECT * FROM users WHERE username = ?', (user,))
        if not c.fetchone(): create_user(conn, user, default_pass)

# --- 5. STATE MANAGEMENT ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ''
if 'edit_mode' not in st.session_state: st.session_state['edit_mode'] = False
if 'data_to_edit' not in st.session_state: st.session_state['data_to_edit'] = None

conn = init_db()
seed_users(conn) 

# ================================
#           LOGIN PAGE
# ================================
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        st.title("🔐 Login Sistem")
        st.info("Password Default: 123456")
        
        tab1, tab2 = st.tabs(["Login", "Daftar User Baru"])
        with tab1:
            u_in = st.text_input("Username")
            p_in = st.text_input("Password", type='password')
            if st.button("Masuk"):
                if login_user(conn, u_in, make_hashes(p_in)):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = u_in
                    st.rerun()
                else: st.error("Login Gagal.")
        with tab2:
            st.subheader("Buat Akun")
            nu = st.text_input("User Baru")
            np = st.text_input("Pass Baru", type='password')
            if st.button("Daftar"):
                if create_user(conn, nu, make_hashes(np)): st.success("Sukses! Silakan login.")
                else: st.warning("Username ada.")
        st.markdown('</div>', unsafe_allow_html=True)

# ================================
#           MAIN APP
# ================================
else:
    # Sidebar Sederhana (Tanpa Toggle Dark Mode)
    st.sidebar.title(f"Halo, {st.session_state['username']}")
    
    if st.sidebar.button("Log Out"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ''
        st.rerun()
    st.sidebar.markdown("---")
    
    with st.container():
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        st.title("📝 Aktivitas Harian")
        
        menu = ["Input Aktivitas", "Laporan & Filter"]
        choice = st.sidebar.radio("Navigasi", menu)

        # --- HALAMAN INPUT ---
        if choice == "Input Aktivitas":
            if st.session_state['edit_mode']:
                st.subheader(f"✏️ Edit Data (ID: {st.session_state['data_to_edit']['id']})")
                dt = st.session_state['data_to_edit']
                d_tgl = datetime.strptime(dt['tanggal'], '%Y-%m-%d').date()
                d_wkt, d_akt, d_hsl = dt['waktu'], dt['aktivitas'], dt['hasil']
                btn_lbl = "Update Data"
            else:
                st.subheader("➕ Input Baru")
                d_tgl = datetime.now()
                d_wkt, d_akt, d_hsl = "08.00 - 10.00", "", ""
                btn_lbl = "Simpan"

            with st.form("input_form"):
                col_a, col_b = st.columns(2)
                with col_a: tgl = st.date_input("Tanggal *", d_tgl)
                with col_b: 
                    opsi = ["08.00 - 10.00", "10.00 - 12.00", "13.00 - 15.00", "15.00 - 17.00"]
                    wkt = st.selectbox("Waktu *", opsi, index=opsi.index(d_wkt) if d_wkt in opsi else 0)
                
                akt = st.text_area("Uraian Kegiatan *", value=d_akt, height=100)
                hsl = st.text_area("Hasil / Output *", value=d_hsl, height=100)
                
                if st.form_submit_button(btn_lbl, use_container_width=True, type="primary"):
                    if akt and hsl:
                        curr = st.session_state['username']
                        if st.session_state['edit_mode']:
                            update_data(conn, st.session_state['data_to_edit']['id'], tgl, wkt, akt, hsl)
                            st.success("Data diupdate!")
                            st.session_state['edit_mode'] = False
                            st.session_state['data_to_edit'] = None
                            st.rerun()
                        else:
                            add_data(conn, curr, tgl, wkt, akt, hsl)
                            st.success("Tersimpan!")
                            st.rerun()
                    else: st.error("Lengkapi data.")
            
            if st.session_state['edit_mode']:
                if st.button("Batal Edit"):
                    st.session_state['edit_mode'] = False; st.session_state['data_to_edit'] = None; st.rerun()

        # --- HALAMAN LAPORAN ---
        elif choice == "Laporan & Filter":
            st.subheader("📊 Laporan Harian")
            
            # Filter
            c1, c2 = st.columns(2)
            with c1: start_d = st.date_input("Dari", date(2025, 1, 1))
            with c2: end_d = st.date_input("Sampai", datetime.now())
            
            # Ambil Data
            raw_data = view_data_filtered(conn, st.session_state['username'], start_d, end_d)
            
            if raw_data:
                # Grouping Data
                df = pd.DataFrame(raw_data, columns=['ID', 'Tanggal', 'Waktu', 'Uraian', 'Hasil'])
                df['Tanggal_Indo'] = df['Tanggal'].apply(format_indo)
                
                grouped_df = df.groupby('Tanggal').agg({
                    'Tanggal_Indo': 'first',
                    'Waktu': list,
                    'Uraian': list,
                    'Hasil': list,
                    'ID': list
                }).sort_values('Tanggal', ascending=False).reset_index()
                
                # HTML Table Render
                html_table = """
                <table class="report-table">
                    <thead>
                        <tr>
                            <th style="width: 5%;">No</th>
                            <th style="width: 20%;">Tanggal/Bulan</th>
                            <th style="width: 40%;">Uraian Kegiatan</th>
                            <th style="width: 15%;">Waktu</th>
                            <th style="width: 20%;">Hasil</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                
                for idx, row in grouped_df.iterrows():
                    uraian_html = ""
                    waktu_html = ""
                    hasil_html = ""
                    
                    for i, (w, u, h) in enumerate(zip(row['Waktu'], row['Uraian'], row['Hasil'])):
                        uraian_html += f'<div class="cell-item"><b>{i+1}.</b> {u}</div>'
                        waktu_html += f'<div class="cell-item">{w}</div>'
                        hasil_html += f'<div class="cell-item">{h}</div>'
                    
                    html_table += f"""
                    <tr>
                        <td style="text-align: center;">{idx + 1}</td>
                        <td style="font-weight: bold;">{row['Tanggal_Indo']}</td>
                        <td>{uraian_html}</td>
                        <td style="text-align: center;">{waktu_html}</td>
                        <td>{hasil_html}</td>
                    </tr>
                    """
                html_table += "</tbody></table>"
                
                st.markdown(html_table, unsafe_allow_html=True)
                
                # Export Button
                st.write("")
                df_export = df.copy()
                df_export['Tanggal'] = df_export['Tanggal_Indo']
                st.download_button("📥 Download Excel/CSV", df_export.to_csv(index=False).encode('utf-8'), f"Laporan_{date.today()}.csv", "text/csv")

                st.divider()
                st.markdown("### 🛠️ Edit / Hapus Data")
                
                # Edit/Delete Management
                for i, r in df.iterrows():
                    with st.expander(f"{r['Tanggal_Indo']} - {r['Waktu']} - {r['Uraian'][:30]}..."):
                        c_edit, c_del = st.columns([1, 1])
                        if c_edit.button("✏️ Edit", key=f"e_{r['ID']}"):
                            st.session_state['edit_mode'] = True
                            st.session_state['data_to_edit'] = {'id': r['ID'], 'tanggal': r['Tanggal'], 'waktu': r['Waktu'], 'aktivitas': r['Uraian'], 'hasil': r['Hasil']}
                            st.rerun()
                        if c_del.button("🗑️ Hapus", key=f"d_{r['ID']}"):
                            delete_data(conn, r['ID'])
                            st.success("Terhapus")
                            st.rerun()
            else:
                st.info("Belum ada data.")

        st.markdown('</div>', unsafe_allow_html=True)