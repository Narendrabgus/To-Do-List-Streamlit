import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# --- 1. KONFIGURASI HALAMAN & CSS (UI SEPERTI GAMBAR) ---
st.set_page_config(page_title="Log Aktivitas", layout="wide", page_icon="📝")

# CSS Kustom untuk Background Biru dan Card Putih
st.markdown("""
    <style>
    /* --- BAGIAN 1: LAYOUT UTAMA --- */
    .stApp {
        background-color: #0033cc; /* Warna Background Biru */
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* --- BAGIAN 2: TEKS & LABEL --- */
    h1, h2, h3, h4, h5, p, div, span {
        color: #000000 !important;
    }
    
    label, .stDateInput label, .stSelectbox label, .stTextArea label {
        color: #333333 !important;
        font-weight: bold;
    }

    /* ============================================================ */
    /* BAGIAN 3: WARNA TABEL & GRID (YANG ANDA MINTA)        */
    /* ============================================================ */

    /* A. Garis Pemisah (Grid) pada List dengan Tombol Edit */
    hr {
        /* Ubah #cccccc jadi #000000 (Hitam) atau #ff0000 (Merah) agar jelas */
        border-top: 2px solid #cccccc !important; 
        opacity: 1;
    }

    /* B. Grid untuk st.table (Jika dipakai) */
    [data-testid="stTable"] {
        border: 1px solid #333333 !important;
    }
    [data-testid="stTable"] th {
        background-color: #f0f2f6 !important;
        border-bottom: 2px solid #333333 !important;
    }
    [data-testid="stTable"] td {
        border-bottom: 1px solid #cccccc !important;
    }

    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE FUNCTION (BACKEND) ---
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
    conn.commit()
    return conn

# Fungsi Tambah Data
def add_data(conn, user, tanggal, waktu, aktivitas, hasil):
    c = conn.cursor()
    c.execute('INSERT INTO logs (user, tanggal, waktu, aktivitas, hasil) VALUES (?, ?, ?, ?, ?)',
              (user, tanggal, waktu, aktivitas, hasil))
    conn.commit()

# Fungsi Update Data
def update_data(conn, id, tanggal, waktu, aktivitas, hasil):
    c = conn.cursor()
    c.execute('UPDATE logs SET tanggal=?, waktu=?, aktivitas=?, hasil=? WHERE id=?',
              (tanggal, waktu, aktivitas, hasil, id))
    conn.commit()

# Fungsi Hapus Data
def delete_data(conn, id):
    c = conn.cursor()
    c.execute('DELETE FROM logs WHERE id=?', (id,))
    conn.commit()

# Fungsi Ambil Data (Dengan Filter Tanggal)
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

# --- 3. STATE MANAGEMENT (PENTING UNTUK EDIT) ---
if 'edit_mode' not in st.session_state:
    st.session_state['edit_mode'] = False
    st.session_state['data_to_edit'] = None

# --- 4. UI & LOGIC (FRONTEND) ---
conn = init_db()

# Container Putih Utama (Simulasi Card UI)
with st.container():
    st.markdown('<div class="main-container">', unsafe_allow_html=True)

    # Header
    st.title("📝 Aktivitas Harian")
    
    # Sidebar Login
    users = ["User A", "User B", "User C"]
    selected_user = st.sidebar.selectbox("👤 Profil Pengguna", users)
    st.sidebar.markdown("---")
    
    # Navigasi Sidebar
    menu = ["Input Aktivitas", "Laporan & Filter"]
    choice = st.sidebar.radio("Navigasi", menu)

    # ==========================
    # HALAMAN 1: INPUT / EDIT
    # ==========================
    if choice == "Input Aktivitas":
        # Logika Judul Berubah jika sedang Edit
        if st.session_state['edit_mode']:
            st.subheader(f"✏️ Edit Aktivitas (ID: {st.session_state['data_to_edit']['id']})")
            # Set nilai default form dari data yang mau diedit
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

        # Form Input
        with st.form("input_form", clear_on_submit=False): # Jangan clear otomatis agar kita bisa handle sendiri
            tanggal = st.date_input("Tanggal *", default_tanggal)
            
            waktu_opsi = ["08.00 - 10.00", "10.00 - 12.00", "13.00 - 15.00", "15.00 - 17.00"]
            # Pastikan opsi waktu edit ada di list, jika tidak pilih index 0
            idx_waktu = waktu_opsi.index(default_waktu) if default_waktu in waktu_opsi else 0
            waktu = st.selectbox("Waktu *", waktu_opsi, index=idx_waktu)
            
            aktivitas = st.text_area("Uraian Kegiatan *", value=default_aktivitas, height=100)
            hasil = st.text_area("Hasil / Catatan Penting *", value=default_hasil, height=100)
            
            submitted = st.form_submit_button(btn_label, use_container_width=True, type="primary")
            
            if submitted:
                if aktivitas and hasil:
                    if st.session_state['edit_mode']:
                        # --- PROSES UPDATE ---
                        update_data(conn, st.session_state['data_to_edit']['id'], tanggal, waktu, aktivitas, hasil)
                        st.success("✅ Data berhasil diperbarui!")
                        # Reset Mode Edit
                        st.session_state['edit_mode'] = False
                        st.session_state['data_to_edit'] = None
                        st.rerun() # Refresh halaman
                    else:
                        # --- PROSES SIMPAN BARU ---
                        add_data(conn, selected_user, tanggal, waktu, aktivitas, hasil)
                        st.success("✅ Data baru berhasil disimpan!")
                        st.rerun()
                else:
                    st.error("⚠️ Harap isi Uraian Kegiatan dan Hasil.")
        
        # Tombol Batal Edit
        if st.session_state['edit_mode']:
            if st.button("Batal Edit"):
                st.session_state['edit_mode'] = False
                st.session_state['data_to_edit'] = None
                st.rerun()

    # ==========================
    # HALAMAN 2: LAPORAN & FILTER
    # ==========================
    elif choice == "Laporan & Filter":
        st.subheader("📊 Laporan & Manajemen Data")
        
        # --- FITUR FILTER & EXPORT ---
        col_filter1, col_filter2, col_filter3 = st.columns([2, 2, 2])
        
        with col_filter1:
            start_date = st.date_input("Dari Tanggal", date(2025, 1, 1))
        with col_filter2:
            end_date = st.date_input("Sampai Tanggal", datetime.now())
        
        # Ambil data berdasarkan filter
        data_logs = view_data_filtered(conn, selected_user, start_date, end_date)
        
        # Konversi ke DataFrame
        df = pd.DataFrame(data_logs, columns=['ID', 'Tanggal', 'Waktu', 'Uraian', 'Hasil'])
        
        with col_filter3:
            st.write("") # Spacer
            st.write("") # Spacer
            # Export Button
            if not df.empty:
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export ke Excel/CSV",
                    data=csv,
                    file_name=f'laporan_{selected_user}_{date.today()}.csv',
                    mime='text/csv',
                )
        
        st.divider()

        # --- TAMPILAN TABEL CUSTOM (UNTUK FITUR EDIT/DELETE) ---
        # Karena st.dataframe tidak bisa punya tombol edit/delete per baris,
        # kita buat tampilan list manual menggunakan st.columns
        
        if not df.empty:
            # Header Tabel
            h1, h2, h3, h4, h5 = st.columns([2, 2, 4, 3, 2])
            h1.markdown("**Tanggal**")
            h2.markdown("**Waktu**")
            h3.markdown("**Uraian**")
            h4.markdown("**Hasil**")
            h5.markdown("**Aksi**")
            st.markdown("---")
            
            # Loop setiap baris data
            for index, row in df.iterrows():
                # Layout per baris
                c1, c2, c3, c4, c5 = st.columns([2, 2, 4, 3, 2])
                
                c1.write(row['Tanggal'])
                c2.write(row['Waktu'])
                c3.write(row['Uraian']) # Text area wrap otomatis
                c4.write(row['Hasil'])
                
                # Kolom Aksi (Tombol Edit & Delete)
                with c5:
                    # Tombol Edit
                    if st.button("✏️", key=f"edit_{row['ID']}", help="Edit Data ini"):
                        # Simpan data ke session state
                        st.session_state['edit_mode'] = True
                        st.session_state['data_to_edit'] = {
                            'id': row['ID'],
                            'tanggal': row['Tanggal'],
                            'waktu': row['Waktu'],
                            'aktivitas': row['Uraian'],
                            'hasil': row['Hasil']
                        }
                        # Pindah ke menu Input secara otomatis (trik switch page manual)
                        # Karena st.sidebar.radio tidak bisa diubah lewat code dengan mudah,
                        # kita minta user pindah manual atau gunakan st.rerun dengan logic tambahan.
                        # Di sini kita beri notifikasi saja.
                        st.success("Mode Edit Aktif! Silakan pindah ke menu 'Input Aktivitas'.")
                        
                    # Tombol Delete dengan Konfirmasi
                    if st.button("🗑️", key=f"del_{row['ID']}", help="Hapus Data ini"):
                        # Tampilkan konfirmasi di bawah tombol
                        st.session_state[f'confirm_del_{row["ID"]}'] = True
                    
                    # Logic Konfirmasi Hapus
                    if st.session_state.get(f'confirm_del_{row["ID"]}'):
                        st.warning("Hapus?")
                        col_y, col_n = st.columns(2)
                        if col_y.button("Ya", key=f"y_{row['ID']}"):
                            delete_data(conn, row['ID'])
                            st.success("Terhapus")
                            st.rerun()
                        if col_n.button("Batal", key=f"n_{row['ID']}"):
                            st.session_state[f'confirm_del_{row["ID"]}'] = False
                            st.rerun()
                
                st.markdown("---") # Garis pemisah antar baris
        else:
            st.info("Tidak ada data ditemukan pada rentang tanggal tersebut.")

    st.markdown('</div>', unsafe_allow_html=True) # Tutup div main-container