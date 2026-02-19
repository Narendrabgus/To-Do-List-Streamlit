import streamlit as st
import pandas as pd
import hashlib
import io
import xlsxwriter
import base64
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="LKPKT Ombudsman", layout="wide", page_icon="📝")

# --- SLOT WAKTU OTOMATIS ---
TIME_SLOTS = [
    "08.00 - 10.00", "10.00 - 12.00", "13.00 - 15.00", "15.00 - 17.00"
]

# --- 2. KONEKSI GOOGLE SHEETS ---
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

def get_img_as_base64(file):
    try:
        with open(file, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return ""

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

# --- 4. LOAD ASSETS ---
# bg_ombudsman tidak lagi dipakai sebagai background utama, tapi dibiarkan agar tidak error jika dipanggil
bg_ombudsman = get_img_as_base64("GambarOmbudsman.jpeg") 
bg_sidebar = get_img_as_base64("sidebar_bg.webp")
logo_udinus = get_img_as_base64("LogoUdinus.png")

# --- CSS CUSTOM STYLE ---
st.markdown(f"""
    <style>
    /* HEADER TRANSPARAN */
    [data-testid="stHeader"] {{
        background-color: rgba(0,0,0,0);
        color: white !important;
    }}
    
    /* 1. BACKGROUND UTAMA (Warna Biru Solid) */
    /* KITA UBAH BAGIAN INI */
    .stApp {{
        background-image: none !important; /* Hapus gambar */
        background-color: #1A73E8 !important; /* Ganti dengan warna biru */
    }}

    /* 2. SIDEBAR BACKGROUND */
    [data-testid="stSidebar"] {{
        background-color: rgba(255, 255, 255, 0.55) !important;
    }}
    [data-testid="stSidebar"]::before {{
        content: ""; position: absolute; top: 50%; left: 50%;
        width: 100vh; height: 100vh;
        background-image: url("data:image/webp;base64,{bg_sidebar}");
        background-size: contain; background-position: center; background-repeat: no-repeat;
        transform: translate(-50%, -50%) rotate(-90deg);
        z-index: -1; opacity: 0.15;
        pointer-events: none; 
    }}

    /* 3. CONTAINER BOX (Background putih solid/transparan) */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: rgba(255, 255, 255, 0.95) !important; /* Putih 95% */
        border-radius: 15px !important;
        padding: 2rem !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
    }}
    
    /* Memastikan semua teks di dalam container berwarna HITAM */
    [data-testid="stVerticalBlockBorderWrapper"] * {{
        color: black !important;
    }}

    /* Styling Input Field */
    [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {{
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ccc !important;
    }}
    
    /* 4. WATERMARK UDINUS */
    .watermark-container {{
        position: fixed;
        bottom: 15px;
        right: 15px;
        background-color: rgba(255, 255, 255, 0.9);
        padding: 8px 15px;
        border-radius: 50px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        display: flex;
        align-items: center;
        gap: 10px;
        z-index: 9999;
        border: 1px solid #ddd;
    }}
    .watermark-logo {{
        width: 35px;
        height: auto;
    }}
    .watermark-text {{
        font-family: 'Arial', sans-serif;
        font-size: 12px;
        font-weight: bold;
        color: #003366 !important;
        margin: 0;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- INJECT HTML WATERMARK ---
st.markdown(f"""
    <div class="watermark-container">
        <img src="data:image/png;base64,{logo_udinus}" class="watermark-logo">
        <span class="watermark-text">Universitas Dian Nuswantoro</span>
    </div>
""", unsafe_allow_html=True)


# --- 5. DATABASE OPERATIONS ---
def load_logs():
    conn = get_conn()
    try: return conn.read(worksheet="logs", ttl=0)
    except: return pd.DataFrame(columns=["user", "tanggal", "waktu", "aktivitas", "hasil", "id"])

def load_users():
    conn = get_conn()
    try:
        df = conn.read(worksheet="users", ttl=0)
        if 'username' not in df.columns or 'password' not in df.columns: 
            return pd.DataFrame(columns=["username", "password"])
        return df
    except Exception as e:
        return pd.DataFrame(columns=["username", "password"])

def add_data(user, tanggal, waktu, aktivitas, hasil):
    conn = get_conn(); df_logs = load_logs()
    new_id = 1
    if not df_logs.empty and 'id' in df_logs.columns:
        df_logs['id'] = pd.to_numeric(df_logs['id'], errors='coerce').fillna(0)
        if len(df_logs) > 0: new_id = int(df_logs['id'].max()) + 1
    new_row = pd.DataFrame([{"user": user, "tanggal": str(tanggal), "waktu": waktu, "aktivitas": aktivitas, "hasil": hasil, "id": new_id}])
    conn.update(worksheet="logs", data=pd.concat([df_logs, new_row], ignore_index=True))

def create_user(username, password):
    df_users = load_users()
    if df_users.empty: pass 
    elif username in df_users['username'].values: return False
    conn = get_conn()
    new_row = pd.DataFrame([{"username": username, "password": password}])
    conn.update(worksheet="users", data=pd.concat([df_users, new_row], ignore_index=True))
    return True

def delete_data(log_id):
    conn = get_conn(); df_logs = load_logs()
    df_logs['id'] = pd.to_numeric(df_logs['id'], errors='coerce')
    conn.update(worksheet="logs", data=df_logs[df_logs['id'] != log_id])

def update_data_log(log_id, tanggal, waktu, aktivitas, hasil):
    conn = get_conn(); df_logs = load_logs()
    df_logs['id'] = pd.to_numeric(df_logs['id'], errors='coerce')
    idx = df_logs.index[df_logs['id'] == log_id].tolist()
    if idx:
        df_logs.at[idx[0], 'tanggal'] = str(tanggal); df_logs.at[idx[0], 'waktu'] = waktu
        df_logs.at[idx[0], 'aktivitas'] = aktivitas; df_logs.at[idx[0], 'hasil'] = hasil
        conn.update(worksheet="logs", data=df_logs)

def get_filtered_logs(user, start_date, end_date):
    df = load_logs()
    if df.empty: return []
    df = df[df['user'] == user]
    df['tanggal_dt'] = pd.to_datetime(df['tanggal']).dt.date
    mask = (df['tanggal_dt'] >= start_date) & (df['tanggal_dt'] <= end_date)
    df_filtered = df.loc[mask].sort_values(by=['tanggal', 'waktu'], ascending=[False, True])
    return df_filtered[['id', 'tanggal', 'waktu', 'aktivitas', 'hasil']].values.tolist()

def count_activity_per_day(user, tanggal):
    df = load_logs(); 
    if df.empty: return 0
    df = df[df['user'] == user]; df['tanggal'] = df['tanggal'].astype(str)
    return len(df[df['tanggal'] == str(tanggal)])

def seed_users_gsheet():
    df_users = load_users()
    if df_users is None or (df_users.empty and "username" not in df_users.columns): return
    if df_users.empty or len(df_users) == 0:
        default_users = ["Elisa Luhulima", "Ahmad Sobirin", "Dewi Puspita Sari", "Anni Samudra Wulan", "Nafi Alrasyid", "Muhamad Ichsan Kamil", "Oscar Gideon", "Rafael Yolens Putera Larung", "Izzat Nabela Ali", "Katrin Dian Lestari", "Diah", "Gary", "Rika"]
        pass_hash = make_hashes("123456")
        new_data = []; 
        for u in default_users: new_data.append({"username": u, "password": pass_hash})
        try: conn = get_conn(); conn.update(worksheet="users", data=pd.DataFrame(new_data)); st.toast("Init Users OK", icon="✅")
        except: pass

# --- SESSION & INIT ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ''
if 'jumlah_input' not in st.session_state: st.session_state['jumlah_input'] = 1
if 'edit_mode' not in st.session_state: st.session_state['edit_mode'] = False
if 'data_to_edit' not in st.session_state: st.session_state['data_to_edit'] = None
seed_users_gsheet()

# ================= LOGIN / SIGN UP =================
if not st.session_state['logged_in']:
    # Menggunakan Layout Kolom untuk menengahkan Form Login
    c1, c2, c3 = st.columns([1, 2, 1])
    
    with c2:
        # PENTING: Container ini yang akan diberi background putih oleh CSS
        with st.container(border=True):
            st.title("LKPKT") 
            st.markdown("### Laporan Kinerja & Pencatatan Kegiatan Harian")
            st.divider()

            tab1, tab2 = st.tabs(["Login", "Daftar"])
            
            with tab1:
                u_in = st.text_input("Username", key="l_u")
                p_in = st.text_input("Password", type="password", key="l_p")
                if st.button("Masuk"):
                    users = load_users()
                    if not users.empty and u_in in users['username'].values:
                        stored_pass = users[users['username']==u_in]['password'].values[0]
                        if stored_pass == make_hashes(p_in):
                            st.session_state['logged_in'] = True; st.session_state['username'] = u_in; st.rerun()
                        else: st.error("Password Salah")
                    else: 
                        st.error("User tidak ditemukan atau Gagal Koneksi.")

            with tab2:
                nu = st.text_input("User Baru", key="s_u"); np = st.text_input("Pass Baru", type="password", key="s_p"); npc = st.text_input("Ulangi Pass", type="password", key="s_pc")
                if st.button("Daftar"):
                    if np == npc and np:
                        if create_user(nu, make_hashes(np)): st.success("Sukses! Login sekarang.")
                        else: st.warning("User sudah ada atau Gagal Koneksi.")
                    else: st.error("Password beda / kosong.")

# ================= MAIN APP =================
else:
    st.sidebar.title(f"Halo, {st.session_state['username']}")
    if st.sidebar.button("Log Out"): st.session_state['logged_in'] = False; st.session_state['username'] = ''; st.rerun()

    menu = ["Input Aktivitas", "Laporan & Filter"]
    choice = st.sidebar.radio("Navigasi", menu)

    # CONTAINER UTAMA UNTUK ISI APLIKASI
    with st.container(border=True):
        if choice == "Input Aktivitas":
            if st.session_state['edit_mode']:
                st.title("✏️ Edit Aktivitas")
                dt = st.session_state['data_to_edit']
                with st.form("edit_form"):
                    e_tgl = st.date_input("Tanggal", datetime.strptime(dt['tanggal'], '%Y-%m-%d').date())
                    e_wkt_idx = TIME_SLOTS.index(dt['waktu']) if dt['waktu'] in TIME_SLOTS else 0
                    e_wkt = st.selectbox("Waktu", TIME_SLOTS, index=e_wkt_idx)
                    e_akt = st.text_area("Uraian", value=dt['aktivitas']); e_hsl = st.text_area("Hasil", value=dt['hasil'])
                    if st.form_submit_button("Update Data"):
                        update_data_log(dt['id'], e_tgl, e_wkt, e_akt, e_hsl)
                        st.success("Data Diperbarui!"); st.session_state['edit_mode'] = False; st.session_state['data_to_edit'] = None; st.rerun()
                if st.button("Batal Edit"): st.session_state['edit_mode'] = False; st.session_state['data_to_edit'] = None; st.rerun()

            else:
                st.title("📝 Input Aktivitas")
                tgl = st.date_input("Pilih Tanggal", datetime.now()); user = st.session_state['username']
                existing = count_activity_per_day(user, tgl); sisa = len(TIME_SLOTS) - existing
                if sisa <= 0: st.warning("Slot penuh hari ini.")
                else:
                    c_add, c_inf = st.columns([1,4])
                    with c_add:
                        if st.button("➕ Tambah"): 
                            if st.session_state['jumlah_input'] < sisa: st.session_state['jumlah_input'] += 1
                    with c_inf: st.caption(f"Terisi: {existing}. Sisa: {sisa}")
                    
                    with st.form("dyn_form"):
                        limit = min(st.session_state['jumlah_input'], sisa); save_list = []
                        for i in range(limit):
                            slot = TIME_SLOTS[existing + i]; st.markdown(f"**Slot: {slot}**")
                            a = st.text_area("Uraian", key=f"a_{i}"); h = st.text_area("Hasil", key=f"h_{i}")
                            save_list.append({"t":tgl, "w":slot, "a":a, "h":h}); st.divider()
                        if st.form_submit_button("Simpan Semua"):
                            n = 0
                            for d in save_list:
                                if d['a'] and d['h']: add_data(user, d['t'], d['w'], d['a'], d['h']); n += 1
                            if n > 0: 
                                st.success(f"{n} Data Tersimpan!")
                                st.session_state['jumlah_input'] = 1
                                st.rerun()
                            else: 
                                st.error("Isi data dulu.")

        elif choice == "Laporan & Filter":
            st.title("📊 Laporan")
            c1, c2 = st.columns(2)
            with c1: sd = st.date_input("Dari", date(2025,1,1))
            with c2: ed = st.date_input("Sampai", datetime.now())
            
            raw = get_filtered_logs(st.session_state['username'], sd, ed)
            df = pd.DataFrame(raw, columns=['ID','Tanggal','Waktu','Uraian','Hasil'])
            
            if not df.empty:
                df_excel = df.copy()
                df_excel['Tanggal_dt'] = pd.to_datetime(df_excel['Tanggal'])
                df_excel = df_excel.sort_values(by=['Tanggal_dt', 'Waktu'], ascending=[True, True])
                df_excel['Tanggal'] = df_excel['Tanggal_dt'].apply(format_indo)
                
                excel_data = generate_excel(df_excel[['ID','Tanggal','Waktu','Uraian','Hasil']])
                st.download_button("📥 Download Excel (Terlama di Atas)", excel_data, f"Laporan_Log.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                
                df['Tanggal_Indo'] = df['Tanggal'].apply(format_indo)
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
                                        st.session_state['edit_mode'] = True; st.session_state['data_to_edit'] = {'id': r['ID'], 'tanggal': r['Tanggal'], 'waktu': r['Waktu'], 'aktivitas': r['Uraian'], 'hasil': r['Hasil']}; st.rerun()
                                    if st.button("🗑️", key=f"d_{r['ID']}"):
                                        delete_data(r['ID']); st.toast("Terhapus!"); st.rerun()
                                st.caption("---")
            else: st.info("Kosong.")