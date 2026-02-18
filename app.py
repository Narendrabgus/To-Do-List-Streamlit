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

# --- 2. HELPER FUNCTIONS ---
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

# --- FUNGSI EXCEL (DIPERBARUI: MERGE CELLS) ---
def generate_excel(df):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Laporan')

    # Format Header
    header_fmt = workbook.add_format({
        'bold': True, 'font_color': '#000000', 'bg_color': '#9bc2e6',
        'border': 1, 'align': 'center', 'valign': 'vcenter'
    })
    
    # Format Isi Biasa (Rata Kiri, Wrap Text)
    body_fmt = workbook.add_format({
        'text_wrap': True, 'border': 1, 'valign': 'top', 'align': 'left'
    })
    
    # Format Tengah (ID, Waktu)
    center_fmt = workbook.add_format({
        'text_wrap': True, 'border': 1, 'valign': 'top', 'align': 'center'
    })

    # Format Tanggal (Tengah Vertical & Horizontal) - Khusus untuk Merge
    date_merge_fmt = workbook.add_format({
        'text_wrap': True, 'border': 1, 'valign': 'vcenter', 'align': 'center'
    })

    # Tulis Header
    headers = ['ID', 'Tanggal', 'Waktu', 'Uraian Kegiatan', 'Hasil']
    for col, h in enumerate(headers):
        worksheet.write(0, col, h, header_fmt)

    # --- LOGIKA BARU: GROUPING & MERGING ---
    # Kita kelompokkan data berdasarkan Tanggal agar tahu mana yang harus di-merge
    grouped = df.groupby('Tanggal', sort=False)
    
    current_row = 1 # Mulai dari baris ke-2 (index 1) karena baris 0 adalah header

    for date_val, group in grouped:
        num_rows = len(group)
        first_row = current_row
        last_row = current_row + num_rows - 1
        
        # 1. TULIS KOLOM TANGGAL (MERGED JIKA PERLU)
        if num_rows > 1:
            # Jika ada lebih dari 1 aktivitas di hari yang sama, gabungkan sel (Merge)
            # Kolom Tanggal ada di index 1 (Kolom B)
            worksheet.merge_range(first_row, 1, last_row, 1, str(date_val), date_merge_fmt)
        else:
            # Jika cuma 1 aktivitas, tulis biasa
            worksheet.write(first_row, 1, str(date_val), center_fmt)

        # 2. TULIS SISA KOLOM (ID, Waktu, Uraian, Hasil)
        # Loop untuk setiap baris dalam grup tanggal tersebut
        for _, row_data in group.iterrows():
            # Kolom 0: ID
            worksheet.write(current_row, 0, row_data['ID'], center_fmt)
            # Kolom 1: Tanggal (Sudah dihandle di atas)
            # Kolom 2: Waktu
            worksheet.write(current_row, 2, row_data['Waktu'], center_fmt)
            # Kolom 3: Uraian
            worksheet.write(current_row, 3, row_data['Uraian'], body_fmt)
            # Kolom 4: Hasil
            worksheet.write(current_row, 4, row_data['Hasil'], body_fmt)
            
            current_row += 1

    # Atur Lebar Kolom
    worksheet.set_column('A:A', 5)  # ID
    worksheet.set_column('B:B', 25) # Tanggal
    worksheet.set_column('C:C', 15) # Waktu
    worksheet.set_column('D:D', 50) # Uraian
    worksheet.set_column('E:E', 30) # Hasil

    workbook.close()
    return output.getvalue()

# --- DATABASE FUNCTIONS ---
def init_db():
    conn = sqlite3.connect('kegiatan.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT, tanggal DATE, waktu TEXT, aktivitas TEXT, hasil TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, password TEXT
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

def seed_users(conn):
    default_users = [
        "Elisa Luhulima", "Ahmad Sobirin", "Dewi Puspita Sari", 
        "Anni Samudra Wulan", "Nafi Alrasyid", "Muhamad Ichsan Kamil", 
        "Oscar Gideon", "Rafael Yolens Putera Larung", "Izzat Nabela Ali", 
        "Katrin Dian Lestari", "Diah", "Gary", "Rika"
    ]
    default_pass = make_hashes("123456") 
    
    c = conn.cursor()
    for user in default_users:
        c.execute('SELECT * FROM users WHERE username = ?', (user,))
        if not c.fetchone():
            c.execute('INSERT INTO users(username, password) VALUES (?,?)', (user, default_pass))
    conn.commit()

def login_user(conn, username):
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    return c.fetchone()

def add_data(conn, user, tanggal, waktu, aktivitas, hasil):
    c = conn.cursor()
    c.execute("INSERT INTO logs (user,tanggal,waktu,aktivitas,hasil) VALUES (?,?,?,?,?)",
              (user, tanggal, waktu, aktivitas, hasil))
    conn.commit()

def view_data_filtered(conn, user, start_date, end_date):
    c = conn.cursor()
    c.execute("""
        SELECT id, tanggal, waktu, aktivitas, hasil
        FROM logs
        WHERE user=? AND tanggal BETWEEN ? AND ?
        ORDER BY tanggal DESC, waktu ASC
    """, (user, start_date, end_date))
    return c.fetchall()

# --- SESSION & INIT ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''
if 'jumlah_input' not in st.session_state:
    st.session_state['jumlah_input'] = 1

conn = init_db()
seed_users(conn)

# ================= LOGIN / SIGN UP =================
if not st.session_state['logged_in']:
    st.title("🔐 Sistem Pencatatan Kegiatan")
    
    tab1, tab2 = st.tabs(["Masuk (Login)", "Daftar Akun Baru"])

    with tab1:
        st.subheader("Login Pengguna")
        st.info("Password Default user lama: 123456")
        u_in = st.text_input("Username", key="login_user")
        p_in = st.text_input("Password", type="password", key="login_pass")

        if st.button("Masuk"):
            user_data = login_user(conn, u_in)
            if user_data and user_data[1] == make_hashes(p_in):
                st.session_state['logged_in'] = True
                st.session_state['username'] = u_in
                st.rerun()
            else:
                st.error("Username atau Password salah.")

    with tab2:
        st.subheader("Buat Akun Baru")
        new_u = st.text_input("Username Baru", key="signup_user")
        new_p = st.text_input("Password Baru", type="password", key="signup_pass")
        new_p_confirm = st.text_input("Ulangi Password", type="password", key="signup_pass_confirm")
        
        if st.button("Daftar"):
            if new_p and new_p_confirm:
                if new_p == new_p_confirm:
                    hashed_new_pass = make_hashes(new_p)
                    if create_user(conn, new_u, hashed_new_pass):
                        st.success(f"Akun '{new_u}' berhasil dibuat! Silakan pindah ke tab 'Masuk' untuk login.")
                    else:
                        st.warning("Username tersebut sudah digunakan. Coba nama lain.")
                else:
                    st.error("Password tidak cocok.")
            else:
                st.error("Mohon lengkapi semua kolom.")

# ================= MAIN APPLICATION =================
else:
    st.sidebar.title(f"Halo, {st.session_state['username']}")
    if st.sidebar.button("Log Out"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ''
        st.rerun()

    menu = ["Input Aktivitas", "Laporan & Filter"]
    choice = st.sidebar.radio("Navigasi", menu)

    # ---------------- PAGE INPUT AKTIVITAS ----------------
    if choice == "Input Aktivitas":
        st.title("📝 Input Aktivitas")

        tgl = st.date_input("Pilih Tanggal", datetime.now())
        user = st.session_state['username']

        existing_count = count_activity_per_day(conn, user, tgl)
        sisa_slot = len(TIME_SLOTS) - existing_count

        if sisa_slot <= 0:
            st.warning("⚠️ Semua slot waktu (4 slot) untuk tanggal ini sudah terisi penuh.")
        else:
            col_add, col_info = st.columns([1, 4])
            with col_add:
                if st.button("➕ Tambah Baris"):
                    if st.session_state['jumlah_input'] < sisa_slot:
                        st.session_state['jumlah_input'] += 1
                    else:
                        st.toast("Maksimal input tercapai sesuai slot tersisa!", icon="🚫")
            with col_info:
                st.caption(f"Slot terisi di DB: {existing_count}. Sisa slot tersedia: {sisa_slot}.")

            st.write("---")

            with st.form("form_dynamic"):
                jumlah_render = min(st.session_state['jumlah_input'], sisa_slot)
                data_to_save = []

                for i in range(jumlah_render):
                    slot_index = existing_count + i
                    jam_otomatis = TIME_SLOTS[slot_index]

                    st.markdown(f"**Input ke-{i+1} (Slot: {jam_otomatis})**")
                    akt = st.text_area("Uraian Kegiatan", key=f"akt_{i}")
                    hsl = st.text_area("Hasil / Output", key=f"hsl_{i}")
                    
                    data_to_save.append({
                        "waktu": jam_otomatis,
                        "aktivitas": akt,
                        "hasil": hsl
                    })
                    st.markdown("---")

                submitted = st.form_submit_button("Simpan Semua Data")
                
                if submitted:
                    saved_count = 0
                    for item in data_to_save:
                        if item['aktivitas'] and item['hasil']:
                            add_data(conn, user, tgl, item['waktu'], item['aktivitas'], item['hasil'])
                            saved_count += 1
                    
                    if saved_count > 0:
                        st.success(f"Berhasil menyimpan {saved_count} aktivitas!")
                        st.session_state['jumlah_input'] = 1
                        st.rerun()
                    else:
                        st.error("Mohon isi Uraian dan Hasil setidaknya pada satu data.")

    # ---------------- PAGE LAPORAN ----------------
    elif choice == "Laporan & Filter":
        st.title("📊 Laporan")

        c1, c2 = st.columns(2)
        with c1:
            start_d = st.date_input("Dari", date(2025,1,1))
        with c2:
            end_d = st.date_input("Sampai", datetime.now())

        raw = view_data_filtered(conn, st.session_state['username'], start_d, end_d)
        df = pd.DataFrame(raw, columns=['ID','Tanggal','Waktu','Uraian','Hasil'])

        if not df.empty:
            df['Tanggal'] = df['Tanggal'].apply(format_indo)
            
            # Panggil fungsi generate_excel yang baru (dengan Merge Cells)
            excel_data = generate_excel(df)

            st.download_button(
                "📥 Download Laporan (Excel Merged)",
                data=excel_data,
                file_name=f"Laporan_{st.session_state['username']}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.dataframe(df)
        else:
            st.info("Belum ada data.")