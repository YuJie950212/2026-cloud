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
        new
