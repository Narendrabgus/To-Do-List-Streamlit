import streamlit as st
import pandas as pd
import plotly.express as px
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from datetime import datetime
from streamlit_gsheets import GSheetsConnection # Library baru untuk GSheets

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard Keasistenan IV", page_icon="⚖️", layout="wide")

# (Masukkan blok CUSTOM CSS Anda yang panjang di sini seperti sebelumnya)

# --- INIT SESSION STATE UNTUK LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['role'] = None
    st.session_state['username'] = None

# --- FUNGSI KONEKSI GSHEETS ---
def get_data_from_gsheets():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Ambil data Laporan
    df_laporan = conn.read(worksheet="Data_Laporan", ttl=5).dropna(how='all')
    # Ambil data User
    df_user = conn.read(worksheet="Data_User", ttl=5).dropna(how='all')
    
    # Pastikan tipe data teks untuk df_user agar tidak error saat pencarian
    if not df_user.empty:
        df_user = df_user.astype(str)
        
    return df_laporan, df_user, conn

# --- HALAMAN LOGIN & SIGN UP ---
def login_page():
    st.markdown("<h2 style='text-align: center; color: #003366;'>Sistem Monitoring Keasistenan VI</h2>", unsafe_allow_html=True)
    
    # Panggil koneksi ke GSheets
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_user = conn.read(worksheet="Data_User", ttl=5).dropna(how='all')
        if not df_user.empty:
            df_user = df_user.astype(str)
    except Exception as e:
        st.error("Gagal terhubung ke Database User.")
        st.stop()
        
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        tab_login, tab_signup = st.tabs(["🔐 Login", "📝 Sign Up"])
        
        # --- TAB LOGIN ---
        with tab_login:
            with st.form("login_form"):
                input_user = st.text_input("Username")
                input_pass = st.text_input("Password", type="password")
                submit_login = st.form_submit_button("Masuk", use_container_width=True)
                
                if submit_login:
                    if df_user.empty:
                        st.error("Belum ada data pengguna. Silakan Sign Up terlebih dahulu.")
                    else:
                        # Cek kecocokan username dan password
                        user_match = df_user[(df_user['Username'] == input_user) & (df_user['Password'] == input_pass)]
                        
                        if not user_match.empty:
                            st.session_state['logged_in'] = True
                            st.session_state['role'] = user_match.iloc[0]['Role']
                            st.session_state['username'] = user_match.iloc[0]['Nama']
                            st.rerun()
                        else:
                            st.error("Username atau Password salah!")
                            
        # --- TAB SIGN UP ---
        with tab_signup:
            with st.form("signup_form", clear_on_submit=True):
                new_user = st.text_input("Buat Username")
                new_pass = st.text_input("Buat Password", type="password")
                new_nama = st.text_input("Nama Lengkap Asisten")
                submit_signup = st.form_submit_button("Daftar Akun", use_container_width=True)
                
                if submit_signup:
                    if not new_user or not new_pass or not new_nama:
                        st.warning("Semua kolom harus diisi!")
                    elif not df_user.empty and new_user in df_user['Username'].values:
                        st.error("Username sudah terdaftar! Gunakan username lain.")
                    else:
                        # Buat data pengguna baru (Default Role: User)
                        new_row = pd.DataFrame([{
                            "Username": new_user,
                            "Password": new_pass,
                            "Role": "User",
                            "Nama": new_nama
                        }])
                        
                        # Gabungkan dan simpan ke GSheets
                        updated_user_data = pd.concat([df_user, new_row], ignore_index=True) if not df_user.empty else new_row
                        conn.update(worksheet="Data_User", data=updated_user_data)
                        
                        st.success("Akun berhasil dibuat! Silakan pindah ke tab Login untuk masuk.")

# --- HALAMAN UTAMA (DASHBOARD) ---
def main_dashboard():
    # Load Data dari GSheets
    try:
        data, df_user, conn = get_data_from_gsheets()
    except Exception as e:
        st.error("Gagal terhubung ke Database. Pastikan konfigurasi secrets.toml benar.")
        st.stop()

    # Pastikan format tanggal
    has_date = False
    if 'Tanggal Laporan' in data.columns:
        data['Tanggal Laporan'] = pd.to_datetime(data['Tanggal Laporan'], errors='coerce')
        has_date = True

    # Header Dashboard
    st.markdown(f"""
    <div class="header-container">
        <h1 class="header-title">⚖️ Dashboard Monitoring Keasistenan Utama VI</h1>
        <p class="header-subtitle">Selamat datang, {st.session_state['username']} ({st.session_state['role']})</p>
    </div>
    """, unsafe_allow_html=True)

    # --- LOGIKA SIDEBAR BERDASARKAN ROLE ---
    with st.sidebar:
        try:
            st.image("ombudsman logo.png", width=160)
        except:
            st.markdown("**(Logo Ombudsman)**")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()
            
        st.divider()

        # Gunakan data_filtered untuk grafik agar data aslinya tidak tertimpa
        data_filtered = data.copy() if not data.empty else pd.DataFrame(columns=["Tanggal Laporan", "Nomor Arsip", "Nama Pelapor", "Lokasi LM", "Asisten", "Status", "Substansi"])

        # LOGIKA ROLE USER: Otomatis filter data miliknya dan Tampilkan Form
        if st.session_state['role'] == "User":
            if not data_filtered.empty and 'Asisten' in data_filtered.columns:
                data_filtered = data_filtered[data_filtered['Asisten'] == st.session_state['username']]
            
            st.markdown("### 📝 Tambah Laporan Baru")
            with st.form("form_tambah_laporan", clear_on_submit=True):
                new_tgl = st.date_input("Tanggal Laporan")
                new_no = st.text_input("Nomor Arsip / Agenda")
                new_nama_pelapor = st.text_input("Nama Pelapor")
                new_lokasi = st.text_input("Lokasi LM")
                new_status = st.selectbox("Status", ["Proses", "Selesai", "Tutup"])
                new_substansi = st.selectbox("Substansi", ["Ketenagakerjaan", "Kepegawaian", "Kesehatan", "Jaminan Sosial", "Kesejahteraan Sosial"])
                
                btn_simpan = st.form_submit_button("Simpan Data", use_container_width=True)
                
                if btn_simpan:
                    new_laporan = pd.DataFrame([{
                        "Tanggal Laporan": new_tgl.strftime("%Y-%m-%d"),
                        "Nomor Arsip": new_no,
                        "Nama Pelapor": new_nama_pelapor,
                        "Lokasi LM": new_lokasi,
                        "Asisten": st.session_state['username'],
                        "Status": new_status,
                        "Substansi": new_substansi
                    }])
                    
                    updated_data = pd.concat([data, new_laporan], ignore_index=True) if not data.empty else new_laporan
                    conn.update(worksheet="Data_Laporan", data=updated_data)
                    st.success("Data berhasil ditambahkan!")
                    st.rerun()

        # LOGIKA ROLE ADMIN: Bebas filter semua asisten dari database User
        elif st.session_state['role'] == "Admin":
            st.markdown("### 🔎 Pencarian & Filter")
            
            # Ambil daftar nama asisten langsung dari Data_User (hanya yang role-nya User)
            if not df_user.empty:
                daftar_asisten = df_user[df_user['Role'] == 'User']['Nama'].tolist()
                asisten_list = ["Semua Asisten"] + sorted(daftar_asisten)
            else:
                asisten_list = ["Semua Asisten"]
                
            sel_asisten = st.selectbox("👤 Asisten:", asisten_list)
            
            if sel_asisten != "Semua Asisten" and not data_filtered.empty and 'Asisten' in data_filtered.columns:
                data_filtered = data_filtered[data_filtered["Asisten"] == sel_asisten]
        
        # Filter Status (Berlaku untuk User & Admin)
        if not data_filtered.empty and 'Status' in data_filtered.columns:
            status_list = ["Semua Status"] + sorted(data_filtered["Status"].dropna().unique().tolist())
            sel_status = st.multiselect("📊 Status:", status_list, default="Semua Status")
            if "Semua Status" not in sel_status and sel_status:
                data_filtered = data_filtered[data_filtered["Status"].isin(sel_status)]

        # Filter Substansi (Berlaku untuk User & Admin)
        if not data_filtered.empty and 'Substansi' in data_filtered.columns:
            substansi_list = ["Semua Substansi"] + sorted(data_filtered["Substansi"].dropna().unique().tolist())
            sel_substansi = st.selectbox("📑 Substansi:", substansi_list)
            if sel_substansi != "Semua Substansi":
                data_filtered = data_filtered[data_filtered["Substansi"] == sel_substansi]

        st.markdown("---")
        if st.sidebar.button("🖨️ Cetak Laporan ke PDF"):
            js = "window.print();"
            st.components.v1.html(f"<script>{js}</script>", height=0, width=0)
    
    # (Lanjutkan dengan kode SECTION 1: KPI METRICS dan grafik lainnya di sini menggunakan variabel 'data_filtered')
    st.write("Menampilkan", len(data_filtered), "data laporan.")
    st.dataframe(data_filtered, use_container_width=True)

# --- ROUTER APLIKASI ---
if not st.session_state['logged_in']:
    login_page()
else:
    main_dashboard()