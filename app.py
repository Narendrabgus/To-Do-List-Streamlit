import streamlit as st
import pandas as pd
import hashlib
import io
import xlsxwriter
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Log Aktivitas", layout="wide", page_icon="📝")

# --- SLOT WAKTU OTOMATIS ---
TIME_SLOTS = [
    "08.00 - 10.00", "10.00 - 12.00", "13.00 - 15.00", "15.00 - 17.00"
]

# --- 2. KONEKSI GOOGLE SHEETS ---
# Fungsi ini membuat koneksi cached agar cepat
def get_conn():
    return st.connection("gsheets", type=GSheetsConnection)

# --- 3. HELPER FUNCTIONS ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def format_indo(tgl_str):
    try:
        if isinstance(tgl_str, str): tgl_obj = datetime.strptime(tgl_str, '%Y-%m-%d').date()
        else: tgl_obj = tgl_str
        hari = {'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu', 'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'}
        bulan = {1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'}
        return f"{hari[tgl_obj.strftime('%A')]}, {tgl_obj.day} {bulan[tgl_obj.month]} {tgl_obj.year}"
    except: return str(tgl_str)

def generate_excel(df):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Laporan')
    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#9bc2e6', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
    body_fmt = workbook.add_format({'text_wrap': True, 'border': 1, 'valign': 'top', 'align': 'left'})
    center_fmt = workbook.add_format({'text_wrap': True, 'border': 1, 'valign': 'top', 'align': 'center'})
    date_merge_fmt = workbook.add_format({'text_wrap': True, 'border': 1, 'valign': 'vcenter', 'align': 'center'})

    headers = ['ID', 'Tanggal', 'Waktu', 'Uraian Kegiatan', 'Hasil']
    for col, h in enumerate(headers): worksheet.write(0, col, h, header_fmt)

    grouped = df.groupby('Tanggal', sort=False)
    curr_row = 1
    for date_val, group in grouped:
        rows = len(group)
        if rows > 1: worksheet.merge_range(curr_row, 1, curr_row+rows-1, 1, str(date_val), date_merge_fmt)
        else: worksheet.write(curr_row, 1, str(date_val), center_fmt)
        
        for _, r in group.iterrows():
            worksheet.write(curr_row, 0, r['ID'], center_fmt)
            worksheet.write(curr_row, 2, r['Waktu'], center_fmt)
            worksheet.write(curr_row, 3, r['Uraian'], body_fmt)
            worksheet.write(curr_row, 4, r['Hasil'], body_fmt)
            curr_row += 1

    worksheet.set_column('A:A', 5); worksheet.set_column('B:B', 25); worksheet.set_column('C:C', 15)
    worksheet.set_column('D:D', 50); worksheet.set_column('E:E', 30)
    workbook.close()
    return output.getvalue()

# --- 4. DATABASE OPERATIONS (GOOGLE SHEETS VERSION) ---
# Baca Data Logs
def load_logs():
    conn = get_conn()
    # ttl=0 agar data selalu fresh (tidak dicache)
    try:
        return conn.read(worksheet="logs", ttl=0)
    except:
        return pd.DataFrame(columns=["user", "tanggal", "waktu", "aktivitas", "hasil", "id"])

# Baca Data Users
def load_users():
    conn = get_conn()
    try:
        # Coba baca data
        df = conn.read(worksheet="users", ttl=0)
        # Pastikan kolom yang dibutuhkan ada
        if 'username' not in df.columns or 'password' not in df.columns:
            return pd.DataFrame(columns=["username", "password"])
        return df
    except Exception as e:
        # PENTING: Jika error koneksi, return None (JANGAN return kosong)
        # Agar fungsi seeding tidak salah paham.
        return None

# Tambah Data Log
def add_data(user, tanggal, waktu, aktivitas, hasil):
    conn = get_conn()
    df_logs = load_logs()
    
    # Generate ID baru (ambil max id + 1)
    new_id = 1
    if not df_logs.empty and 'id' in df_logs.columns:
        # Pastikan kolom id numerik
        df_logs['id'] = pd.to_numeric(df_logs['id'], errors='coerce').fillna(0)
        if len(df_logs) > 0:
            new_id = int(df_logs['id'].max()) + 1

    new_row = pd.DataFrame([{
        "user": user,
        "tanggal": str(tanggal),
        "waktu": waktu,
        "aktivitas": aktivitas,
        "hasil": hasil,
        "id": new_id
    }])
    
    # Gabung dan Update Sheet
    updated_df = pd.concat([df_logs, new_row], ignore_index=True)
    conn.update(worksheet="logs", data=updated_df)

# Register User Baru
def create_user(username, password):
    conn = get_conn()
    df_users = load_users()
    
    if username in df_users['username'].values:
        return False
    
    new_row = pd.DataFrame([{"username": username, "password": password}])
    updated_df = pd.concat([df_users, new_row], ignore_index=True)
    conn.update(worksheet="users", data=updated_df)
    return True

# Hapus Data (Berdasarkan ID)
def delete_data(log_id):
    conn = get_conn()
    df_logs = load_logs()
    
    # Filter buang ID yang dipilih
    df_logs['id'] = pd.to_numeric(df_logs['id'], errors='coerce')
    updated_df = df_logs[df_logs['id'] != log_id]
    
    conn.update(worksheet="logs", data=updated_df)

# Edit Data
def update_data_log(log_id, tanggal, waktu, aktivitas, hasil):
    conn = get_conn()
    df_logs = load_logs()
    
    df_logs['id'] = pd.to_numeric(df_logs['id'], errors='coerce')
    idx = df_logs.index[df_logs['id'] == log_id].tolist()
    
    if idx:
        df_logs.at[idx[0], 'tanggal'] = str(tanggal)
        df_logs.at[idx[0], 'waktu'] = waktu
        df_logs.at[idx[0], 'aktivitas'] = aktivitas
        df_logs.at[idx[0], 'hasil'] = hasil
        conn.update(worksheet="logs", data=df_logs)

# Filter Data untuk Tampilan
def get_filtered_logs(user, start_date, end_date):
    df = load_logs()
    if df.empty: return []
    
    # Filter User
    df = df[df['user'] == user]
    
    # Filter Tanggal
    df['tanggal_dt'] = pd.to_datetime(df['tanggal']).dt.date
    mask = (df['tanggal_dt'] >= start_date) & (df['tanggal_dt'] <= end_date)
    df_filtered = df.loc[mask].sort_values(by=['tanggal', 'waktu'], ascending=[False, True])
    
    # Rename untuk kompatibilitas kode lama
    return df_filtered[['id', 'tanggal', 'waktu', 'aktivitas', 'hasil']].values.tolist()

# Hitung aktivitas harian untuk slot waktu
def count_activity_per_day(user, tanggal):
    df = load_logs()
    if df.empty: return 0
    df = df[df['user'] == user]
    df['tanggal'] = df['tanggal'].astype(str)
    count = len(df[df['tanggal'] == str(tanggal)])
    return count

# Seed Users (Hanya dijalankan sekali jika tabel kosong)
def seed_users_gsheet():
    df_users = load_users()
    
    # PENGAMAN 1: Jika gagal load (None), jangan lakukan apa-apa.
    if df_users is None:
        return

    # PENGAMAN 2: Hanya seed jika BENAR-BENAR kosong (baris 0)
    if df_users.empty or len(df_users) == 0:
        default_users = ["Elisa Luhulima", "Ahmad Sobirin", "Dewi Puspita Sari", 
                         "Anni Samudra Wulan", "Nafi Alrasyid", "Muhamad Ichsan Kamil", 
                         "Oscar Gideon", "Rafael Yolens Putera Larung", "Izzat Nabela Ali", 
                         "Katrin Dian Lestari", "Diah", "Gary", "Rika"]
        pass_hash = make_hashes("123456")
        
        new_data = []
        for u in default_users:
            new_data.append({"username": u, "password": pass_hash})
        
        conn = get_conn()
        # Gunakan try-except saat update untuk mencegah crash
        try:
            conn.update(worksheet="users", data=pd.DataFrame(new_data))
            st.toast("Database User berhasil di-inisialisasi!", icon="✅")
        except:
            pass

# --- SESSION & INIT ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ''
if 'jumlah_input' not in st.session_state: st.session_state['jumlah_input'] = 1
if 'edit_mode' not in st.session_state: st.session_state['edit_mode'] = False
if 'data_to_edit' not in st.session_state: st.session_state['data_to_edit'] = None

# Jalankan Seeding (Hanya akan mengisi jika sheet users kosong)
seed_users_gsheet()

# ================= LOGIN / SIGN UP =================
if not st.session_state['logged_in']:
    st.title("🔐 Sistem Pencatatan (GSheets)")
    tab1, tab2 = st.tabs(["Login", "Daftar"])
    
    with tab1:
        u_in = st.text_input("Username", key="l_u")
        p_in = st.text_input("Password", type="password", key="l_p")
        if st.button("Masuk"):
            users = load_users()
            if not users.empty and u_in in users['username'].values:
                stored_pass = users[users['username']==u_in]['password'].values[0]
                if stored_pass == make_hashes(p_in):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = u_in
                    st.rerun()
                else: st.error("Password Salah")
            else: st.error("User tidak ditemukan")

    with tab2:
        nu = st.text_input("User Baru", key="s_u")
        np = st.text_input("Pass Baru", type="password", key="s_p")
        npc = st.text_input("Ulangi Pass", type="password", key="s_pc")
        if st.button("Daftar"):
            if np == npc:
                if create_user(nu, make_hashes(np)): st.success("Sukses! Login sekarang.")
                else: st.warning("User sudah ada.")
            else: st.error("Password beda.")

# ================= MAIN APP =================
else:
    st.sidebar.title(f"Halo, {st.session_state['username']}")
    if st.sidebar.button("Log Out"):
        st.session_state['logged_in'] = False; st.session_state['username'] = ''; st.rerun()

    menu = ["Input Aktivitas", "Laporan & Filter"]
    choice = st.sidebar.radio("Navigasi", menu)

    if choice == "Input Aktivitas":
        if st.session_state['edit_mode']:
            st.title("✏️ Edit Aktivitas")
            dt = st.session_state['data_to_edit']
            
            # Form Edit
            with st.form("edit_form"):
                e_tgl = st.date_input("Tanggal", datetime.strptime(dt['tanggal'], '%Y-%m-%d').date())
                e_wkt_idx = TIME_SLOTS.index(dt['waktu']) if dt['waktu'] in TIME_SLOTS else 0
                e_wkt = st.selectbox("Waktu", TIME_SLOTS, index=e_wkt_idx)
                e_akt = st.text_area("Uraian", value=dt['aktivitas'])
                e_hsl = st.text_area("Hasil", value=dt['hasil'])
                
                if st.form_submit_button("Update Data"):
                    update_data_log(dt['id'], e_tgl, e_wkt, e_akt, e_hsl)
                    st.success("Data Diperbarui!")
                    st.session_state['edit_mode'] = False
                    st.session_state['data_to_edit'] = None
                    st.rerun()
            
            if st.button("Batal Edit"):
                st.session_state['edit_mode'] = False; st.session_state['data_to_edit'] = None; st.rerun()

        else:
            st.title("📝 Input Aktivitas")
            tgl = st.date_input("Pilih Tanggal", datetime.now())
            user = st.session_state['username']
            
            existing = count_activity_per_day(user, tgl)
            sisa = len(TIME_SLOTS) - existing
            
            if sisa <= 0: st.warning("Slot penuh hari ini.")
            else:
                c_add, c_inf = st.columns([1,4])
                with c_add:
                    if st.button("➕ Tambah"): 
                        if st.session_state['jumlah_input'] < sisa: st.session_state['jumlah_input'] += 1
                with c_inf: st.caption(f"Terisi: {existing}. Sisa: {sisa}")
                
                with st.form("dyn_form"):
                    limit = min(st.session_state['jumlah_input'], sisa)
                    save_list = []
                    for i in range(limit):
                        slot = TIME_SLOTS[existing + i]
                        st.markdown(f"**Slot: {slot}**")
                        a = st.text_area("Uraian", key=f"a_{i}")
                        h = st.text_area("Hasil", key=f"h_{i}")
                        save_list.append({"t":tgl, "w":slot, "a":a, "h":h})
                        st.divider()
                    
                    if st.form_submit_button("Simpan Semua"):
                        n = 0
                        for d in save_list:
                            if d['a'] and d['h']:
                                add_data(user, d['t'], d['w'], d['a'], d['h'])
                                n += 1
                        if n > 0:
                            st.success(f"{n} Data Tersimpan ke Google Sheets!")
                            st.session_state['jumlah_input'] = 1
                            st.rerun()
                        else: st.error("Isi data dulu.")

    elif choice == "Laporan & Filter":
        st.title("📊 Laporan")
        c1, c2 = st.columns(2)
        with c1: sd = st.date_input("Dari", date(2025,1,1))
        with c2: ed = st.date_input("Sampai", datetime.now())
        
        raw = get_filtered_logs(st.session_state['username'], sd, ed)
        df = pd.DataFrame(raw, columns=['ID','Tanggal','Waktu','Uraian','Hasil'])
        
        if not df.empty:
            df['Tanggal_Indo'] = df['Tanggal'].apply(format_indo)
            # Excel Generator (Rename column temporarily for generator)
            df_ex = df.copy()
            df_ex['Tanggal'] = df_ex['Tanggal_Indo']
            excel_data = generate_excel(df_ex[['ID','Tanggal','Waktu','Uraian','Hasil']])
            
            st.download_button("📥 Download Excel", excel_data, f"Laporan.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            # Manual Table Layout
            gr = df.groupby('Tanggal_Indo', sort=False)
            h1, h2, h3, h4, h5 = st.columns([2, 3, 2, 3, 1])
            h1.markdown('**Tanggal**'); h2.markdown('**Uraian**'); h3.markdown('**Waktu**'); h4.markdown('**Hasil**'); h5.markdown('**Aksi**')
            
            for dt_val, g in gr:
                with st.container():
                    st.divider()
                    cd, cc = st.columns([2, 9])
                    with cd: st.write(dt_val)
                    with cc:
                        for _, r in g.iterrows():
                            cu, cw, ch, ca = st.columns([3,2,3,1])
                            cu.write(f"• {r['Uraian']}"); cw.write(r['Waktu']); ch.write(f"• {r['Hasil']}")
                            with ca:
                                if st.button("✏️", key=f"e_{r['ID']}"):
                                    st.session_state['edit_mode'] = True
                                    st.session_state['data_to_edit'] = {'id': r['ID'], 'tanggal': r['Tanggal'], 'waktu': r['Waktu'], 'aktivitas': r['Uraian'], 'hasil': r['Hasil']}
                                    st.rerun()
                                if st.button("🗑️", key=f"d_{r['ID']}"):
                                    delete_data(r['ID'])
                                    st.toast("Terhapus!")
                                    st.rerun()
                            st.caption("---")
        else: st.info("Kosong.")