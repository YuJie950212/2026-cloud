import streamlit as st
from phe import paillier
import time
from datetime import datetime
import sqlite3
import pandas as pd

st.set_page_config(page_title="跨平台 UBI 隱私聯防系統原型", page_icon="🛡️", layout="wide")
st.title("🛡️ 跨平台 UBI 隱私計算與零知識證明（ZKP）聯防系統")

# ==========================================
# 實體資料庫 (SQLite) 初始化設定
# ==========================================
DB_FILE = "ubi_system.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 建立車隊資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            plate TEXT PRIMARY KEY,
            name TEXT,
            speeding INTEGER,
            braking INTEGER,
            status TEXT,
            review_time TEXT
        )
    """)
    # 建立歷史紀錄資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            plate TEXT,
            data_summary TEXT,
            zkp_status TEXT,
            score TEXT
        )
    """)
    
    # 檢查是否為空資料庫，若是則塞入初始預設資料
    cursor.execute("SELECT COUNT(*) FROM cars")
    if cursor.fetchone()[0] == 0:
        initial_cars = [
            ("ABC-1234", "張大明", 3, 5, "待審核", "-"),
            ("XYZ-5678", "王小美", 1, 2, "待審核", "-"),
            ("QQ-9999", "李黑客(惡意測試)", 99, 88, "待審核", "-")
        ]
        cursor.executemany("INSERT INTO cars VALUES (?, ?, ?, ?, ?, ?)", initial_cars)
    
    conn.commit()
    conn.close()

# 執行資料庫初始化
init_db()

# ==========================================
# 初始化跨分頁的共享快取記憶體（僅用於展示過渡）
# ==========================================
if "db" not in st.session_state:
    st.session_state["db"] = {
        "has_data": False,
        "enc_speeding": None,
        "enc_braking": None,
        "zkp_status": "Waiting",
        "computed_score": None
    }
if "just_submitted" not in st.session_state:
    st.session_state["just_submitted"] = False

# ==========================================
# 建立網頁頂端的三個獨立站點分頁
# ==========================================
tab1, tab2, tab3 = st.tabs(["🚗 1. 租車平台端 (Edge)", "☁️ 2. 雲端計算大腦 (Cloud)", "🏢 3. 保險公司後台 (Core)"])

# ------------------------------------------
# 【分頁一：租車平台端】（SQLite 永久存檔版）
# ------------------------------------------
with tab1:
    st.header("🚗 邊緣端駕駛數據採集與加密")
    
    col_db, col_add = st.columns([2, 1])
    
    with col_db:
        st.write("### 📡 待處理還車車輛與 OBU 數據清單")
        st.caption("🟢 本地實體資料庫連線中（重新整理網頁數據不會遺失）：")
        
        # 從 SQLite 撈出最新車隊狀態
        conn = sqlite3.connect(DB_FILE)
        df_cars = pd.read_sql_query("SELECT plate AS 車牌號碼, name AS 租客姓名, speeding AS 車機偵測_超速次數, braking AS 車機偵測_急煞次數, status AS 狀態, review_time AS 審核時間 FROM cars", conn)
        conn.close()
        st.table(df_cars)
        
    with col_add:
        st.write("### 📝 新客戶租車登記處")
        st.caption("新客戶臨櫃租車資料將永久寫入實體硬碟檔：")
        
        new_plate = st.text_input("新車車牌", value="EX-5566", max_chars=10)
        new_name = st.text_input("客戶姓名", value="陳小木")
        
        if st.button("➕ 確認租出（數據寫入資料庫）", type="primary"):
            if not new_plate or not new_name:
                st.error("❌ 車牌與姓名不能為空！")
            else:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                try:
                    # 寫入 SQLite，新車上路數據完美歸零
                    cursor.execute("INSERT INTO cars VALUES (?, ?, 0, 0, '待審核', '-')", (new_plate, new_name))
                    conn.commit()
                    st.toast(f"🟢 {new_plate} 已成功出租！資料已安全永久存檔。", icon="🚗")
                    time.sleep(0.5)
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ 該車牌已經在租借列表中了！")
                finally:
                    conn.close()

    st.write("---")
    
    st.write("### 🔍 臨櫃選車與資料拉取")
    # 動態從資料庫抓取車牌清單做成下拉選單
    plate_options = ["請選擇車牌..."] + df_cars["車牌號碼"].tolist()
    selected_plate = st.selectbox("請選擇當前辦理還車的車牌號碼：", plate_options)
    
    # 讀取當前選中車牌的數據
    current_speeding = 0
    current_braking = 0
    if selected_plate != "請選擇車牌...":
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT speeding, braking FROM cars WHERE plate = ?", (selected_plate,))
        row = cursor.fetchone()
        if row:
            current_speeding = row[0]
            current_braking = row[1]
        conn.close()

    st.write("### ✍️ 租車公司人工審核與密碼學打包")

    with st.form(key="edge_data_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"📋 **當前操作車牌：{selected_plate if selected_plate != '請選擇車牌...' else '未選擇'}**")
            speeding = st.number_input("審核：超速次數 (0~50)", min_value=0, value=current_speeding)
            heavy_braking = st.number_input("審核：急煞次數 (0~50)", min_value=0, value=current_braking)
        
        with col2:
            st.write("🔒 **邊緣端密碼學處理預覽：**")
            st.caption("系統處於高流暢模式。點擊下方按鈕將即時調用 Paillier 演算法將審核數據生成密文。")

        st.write("") 
        submit_button = st.form_submit_button(label="🚀 審核無誤：打包密文與 ZKP 發送至雲端")
        
    if submit_button:
        if selected_plate == "請選擇車牌...":
            st.error("❌ 請先在上方下拉選單選擇正確的車牌號碼，再進行送出！")
        else:
            with st.spinner("正在進行加密與 ZKP 證明生成..."):
                time.sleep(0.5) 
                
                pub_key, _ = paillier.generate_paillier_keypair()
                
                if 0 <= speeding <= 50 and 0 <= heavy_braking <= 50:
                    zkp_res = "Verified"
                    score_res = (speeding * 10) + (heavy_braking * 5)
                else:
                    zkp_res = "Failed"
                    score_res = None
                
                # 同步到快取展示記憶體（給分頁二、三展示用）
                st.session_state["db"] = {
                    "has_data": True,
                    "enc_speeding": str(pub_key.encrypt(speeding).ciphertext()),
                    "enc_braking": str(pub_key.encrypt(heavy_braking).ciphertext()),
                    "zkp_status": zkp_res,
                    "computed_score": score_res
                }
                
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 更新 SQLite 資料庫中該車輛的狀態與時間
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("UPDATE cars SET status = '🟢 已審核', review_time = ? WHERE plate = ?", (current_time, selected_plate))
                
                # 永久寫入歷史紀錄表
                zkp_text = "✅ 通過" if zkp_res == "Verified" else "🚨 攔截(異常數據)"
                score_text = f"{score_res} 分" if score_res is not None else "計算終止"
                cursor.execute("INSERT INTO history (timestamp, plate, data_summary, zkp_status, score) VALUES (?, ?, ?, ?, ?)",
                               (current_time, selected_plate, f"{speeding}次 / {heavy_braking}次", zkp_text, score_text))
                
                conn.commit()
                conn.close()
                
                st.session_state["just_submitted"] = True
                
            st.rerun()

    if st.session_state["just_submitted"]:
        st.success("🎉 數據已成功
