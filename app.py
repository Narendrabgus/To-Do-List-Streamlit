import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime, date

# --- 1. KONFIGURASI HALAMAN & CSS ---
st.set_page_config(page_title="Log Aktivitas", layout="wide", page_icon="📝")

st.markdown("""
    <style>
    /* --- BAGIAN 1: LAYOUT UTAMA --- */
    .stApp {
        background-color: #0033cc; 
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* --- BAGIAN 2: TEKS & LABEL --- */
    h1, h2, h3, h4, h5, p, div, span {
        color: #000000 !important;
    }
    
    label, .stDateInput label, .stSelectbox label, .stTextArea label, .stTextInput label {
        color: #333333 !important;
        font-weight: bold;
    }

    /* --- BAGIAN 3: WARNA TABEL & GRID --- */
    hr {
        border-top: 2px solid #cccccc !important; 
        opacity: 1;
    }
    
    /* Tombol Logout */
    .stButton button {
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SECURITY FUNCTIONS (HASHING) ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

# --- 3. DATABASE FUNCTION (BACKEND) ---
def init_db():
    conn = sqlite3.connect('kegiatan.db', check_same_thread=False)
    c = conn.cursor()
    
    # Tabel Logs (Data Kegiatan)
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
    
    # Tabel Users (Data Pengguna & Password)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    ''')
    conn.commit()
    return conn

# Fungsi Menambah User Baru
def create_user(conn, username, password):
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password) VALUES (?,?)', (username, password))
        conn.commit()
        return True
    except:
        return False # Gagal jika username sudah ada

# Fungsi Login
def login_user(conn, username, password):
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    data = c.fetchall()
    return data

# --- CRUD Functions (Sama seperti sebelumnya) ---
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
    query = f"""
        SELECT id, tanggal, waktu, aktivitas, hasil 
        FROM logs 
        WHERE user = ? AND tanggal BETWEEN ? AND ? 
        ORDER BY tanggal DESC, waktu ASC
    """
    c.execute(query, (user, start_date, end_date))
    data = c.fetchall()
    return data

# --- 4. PRE-SEEDING DATA (DAFTAR USER AWAL) ---
# Ini dijalankan setiap app start untuk memastikan user default ada
def seed_users(conn):
    default_users = [
        "Elisa Luhulima", "Ahmad Sobirin", "Dewi Puspita Sari", 
        "Anni Samudra Wulan", "Nafi Alrasyid", "Muhamad Ichsan Kamil", 
        "Oscar Gideon", "Rafael Yolens Putera Larung", "Izzat Nabela Ali", 
        "Katrin Dian Lestari", "Diah", "Gary", "Rika"
    ]
    # Password default untuk semua user awal adalah '123456'
    default_pass = make_hashes("123456") 
    
    c = conn.cursor()
    for user in default_users:
        # Cek apakah user sudah ada
        c.execute('SELECT * FROM users WHERE username = ?', (user,))
        if not c.fetchone():
            create_user(conn, user, default_pass)

# --- 5. SESSION STATE MANAGEMENT ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''
if 'edit_mode' not in st.session_state:
    st.session_state['edit_mode'] = False
    st.session_state['data_to_edit'] = None

# --- 6. CORE APP LOGIC ---
conn = init_db()
seed_users(conn) # Jalankan fungsi pendaftaran user otomatis

# === BAGIAN LOGIN (JIKA BELUM LOGGED IN) ===
if not st.session_state['logged_in']:
    
    # Layout Login di tengah menggunakan Columns
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        st.title("🔐 Login Sistem")
        st.info("Password Default: 123456")

        tab1, tab2 = st.tabs(["Login", "Daftar User Baru"])

        # TAB 1: LOGIN
        with tab1:
            username_input = st.text_input("Username")
            password_input = st.text_input("Password", type='password')
            
            if st.button("Masuk"):
                hashed_pswd = make_hashes(password_input)
                result = login_user(conn, username_input, hashed_pswd)
                
                if result:
                    st.success(f"Selamat Datang, {username_input}!")
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username_input
                    st.rerun()
                else:
                    st.error("Username atau Password salah.")

        # TAB 2: REGISTER (TAMBAH USER BARU)
        with tab2:
            st.subheader("Buat Akun Baru")
            new_user = st.text_input("Username Baru")
            new_password = st.text_input("Password Baru", type='password')
            confirm_password = st.text_input("Ulangi Password", type='password')
            
            if st.button("Daftar"):
                if new_password == confirm_password:
                    hashed_new_password = make_hashes(new_password)
                    if create_user(conn, new_user, hashed_new_password):
                        st.success("Akun berhasil dibuat! Silakan login.")
                    else:
                        st.warning("Username sudah terpakai.")
                else:
                    st.error("Password tidak cocok.")
        
        st.markdown('</div>', unsafe_allow_html=True)


# === BAGIAN UTAMA APLIKASI (JIKA SUDAH LOGGED IN) ===
else:
    # Sidebar Logout
    st.sidebar.title(f"Halo, {st.session_state['username']}")
    if st.sidebar.button("Log Out"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ''
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # Container Utama
    with st.container():
        st.markdown('<div class="main-container">', unsafe_allow_html=True)

        st.title("📝 Aktivitas Harian")
        
        menu = ["Input Aktivitas", "Laporan & Filter"]
        choice = st.sidebar.radio("Navigasi", menu)

        # --- HALAMAN INPUT ---
        if choice == "Input Aktivitas":
            if st.session_state['edit_mode']:
                st.subheader(f"✏️ Edit Aktivitas (ID: {st.session_state['data_to_edit']['id']})")
                default_tanggal = datetime.strptime(st.session_state['data_to_edit']['tanggal'], '%Y-%m-%d').date()
                default_waktu = st.session_state['data_to_edit']['waktu']
                default_aktivitas = st.session_state['data_to_edit']['aktivitas']
                default_hasil = st.session_state['data_to_edit']['hasil']
                btn_label = "Update Data"
            else:
                st.subheader(f"➕ Input Aktivitas Baru")
                default_tanggal = datetime.now()
                default_waktu = "08.00 - 10.00"
                default_aktivitas = ""
                default_hasil = ""
                btn_label = "Simpan"

            with st.form("input_form", clear_on_submit=False):
                tanggal = st.date_input("Tanggal *", default_tanggal)
                waktu_opsi = ["08.00 - 10.00", "10.00 - 12.00", "13.00 - 15.00", "15.00 - 17.00"]
                idx_waktu = waktu_opsi.index(default_waktu) if default_waktu in waktu_opsi else 0
                waktu = st.selectbox("Waktu *", waktu_opsi, index=idx_waktu)
                aktivitas = st.text_area("Uraian Kegiatan *", value=default_aktivitas, height=100)
                hasil = st.text_area("Hasil / Catatan Penting *", value=default_hasil, height=100)
                
                submitted = st.form_submit_button(btn_label, use_container_width=True, type="primary")
                
                if submitted:
                    if aktivitas and hasil:
                        # Gunakan st.session_state['username'] sebagai user yang menyimpan data
                        current_user = st.session_state['username']
                        
                        if st.session_state['edit_mode']:
                            update_data(conn, st.session_state['data_to_edit']['id'], tanggal, waktu, aktivitas, hasil)
                            st.success("✅ Data berhasil diperbarui!")
                            st.session_state['edit_mode'] = False
                            st.session_state['data_to_edit'] = None
                            st.rerun()
                        else:
                            add_data(conn, current_user, tanggal, waktu, aktivitas, hasil)
                            st.success("✅ Data baru berhasil disimpan!")
                            st.rerun()
                    else:
                        st.error("⚠️ Harap isi Uraian Kegiatan dan Hasil.")
            
            if st.session_state['edit_mode']:
                if st.button("Batal Edit"):
                    st.session_state['edit_mode'] = False
                    st.session_state['data_to_edit'] = None
                    st.rerun()

        # --- HALAMAN LAPORAN ---
        elif choice == "Laporan & Filter":
            st.subheader("📊 Laporan & Manajemen Data")
            col_filter1, col_filter2, col_filter3 = st.columns([2, 2, 2])
            
            with col_filter1:
                start_date = st.date_input("Dari Tanggal", date(2025, 1, 1))
            with col_filter2:
                end_date = st.date_input("Sampai Tanggal", datetime.now())
            
            # Ambil data HANYA milik user yang sedang login
            current_user = st.session_state['username']
            data_logs = view_data_filtered(conn, current_user, start_date, end_date)
            
            df = pd.DataFrame(data_logs, columns=['ID', 'Tanggal', 'Waktu', 'Uraian', 'Hasil'])
            
            with col_filter3:
                st.write("")
                st.write("")
                if not df.empty:
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Export CSV",
                        data=csv,
                        file_name=f'laporan_{current_user}_{date.today()}.csv',
                        mime='text/csv',
                    )
            
            st.divider()

            if not df.empty:
                h1, h2, h3, h4, h5 = st.columns([2, 2, 4, 3, 2])
                h1.markdown("**Tanggal**")
                h2.markdown("**Waktu**")
                h3.markdown("**Uraian**")
                h4.markdown("**Hasil**")
                h5.markdown("**Aksi**")
                st.markdown("---")
                
                for index, row in df.iterrows():
                    c1, c2, c3, c4, c5 = st.columns([2, 2, 4, 3, 2])
                    c1.write(row['Tanggal'])
                    c2.write(row['Waktu'])
                    c3.write(row['Uraian'])
                    c4.write(row['Hasil'])
                    with c5:
                        if st.button("✏️", key=f"edit_{row['ID']}"):
                            st.session_state['edit_mode'] = True
                            st.session_state['data_to_edit'] = {
                                'id': row['ID'], 'tanggal': row['Tanggal'], 
                                'waktu': row['Waktu'], 'aktivitas': row['Uraian'], 
                                'hasil': row['Hasil']
                            }
                            st.rerun()
                            
                        if st.button("🗑️", key=f"del_{row['ID']}"):
                            st.session_state[f'confirm_del_{row["ID"]}'] = True
                        
                        if st.session_state.get(f'confirm_del_{row["ID"]}'):
                            st.warning("Hapus?")
                            cy, cn = st.columns(2)
                            if cy.button("Ya", key=f"y_{row['ID']}"):
                                delete_data(conn, row['ID'])
                                st.rerun()
                            if cn.button("Batal", key=f"n_{row['ID']}"):
                                st.session_state[f'confirm_del_{row["ID"]}'] = False
                                st.rerun()
                    st.markdown("---")
            else:
                st.info("Tidak ada data ditemukan.")

        st.markdown('</div>', unsafe_allow_html=True)