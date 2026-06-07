import streamlit as st
from phe import paillier
import time
from datetime import datetime
import sqlite3
import pandas as pd

st.set_page_config(page_title="跨平台 UBI 隱私聯防系統原型", page_icon="🛡️", layout="wide")
st.title("🛡️ 跨平台 UBI 隱私計算與零知識證明（ZKP）聯防系統")

DB_FILE = "ubi_system.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            plate TEXT PRIMARY KEY, name TEXT, speeding INTEGER, braking INTEGER, status TEXT, review_time TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, plate TEXT, data_summary TEXT, zkp_status TEXT, score TEXT
        )
    """)
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

init_db()

if "db" not in st.session_state:
    st.session_state["db"] = {"has_data": False, "enc_speeding": None, "enc_braking": None, "zkp_status": "Waiting", "computed_score": None}
if "just_submitted" not in st.session_state:
    st.session_state["just_submitted"] = False

tab1, tab2, tab3 = st.tabs(["🚗 1. 租車平台端 (Edge)", "☁️ 2. 雲端計算大腦 (Cloud)", "🏢 3. 保險公司後台 (Core)"])

# ==========================================
# 【分頁一：租車平台端】
# ==========================================
with tab1:
    st.header("🚗 邊緣端駕駛數據採集與加密")
    col_db, col_add = st.columns([2, 1])
    
    with col_db:
        st.write("### 📡 待處理還車車輛與 OBU 數據清單")
        conn = sqlite3.connect(DB_FILE)
        df_cars = pd.read_sql_query("SELECT plate AS 車牌號碼, name AS 租客姓名, speeding AS 車機偵測_超速次數, braking AS 車機偵測_急煞次數, status AS 狀態, review_time AS 審核時間 FROM cars", conn)
        conn.close()
        st.table(df_cars)
        
    with col_add:
        st.write("### 📝 新客戶租車登記處")
        st.caption("當庫存空車要再次租出，或有全新車輛加入時在此登記：")
        
        # 這裡改成可以輸入現有車牌來更新租客，或者新增全新車牌
        rent_plate = st.text_input("租出車牌 (現有車牌或新車牌)", value="EX-5566", max_chars=10)
        new_name = st.text_input("新客戶姓名", value="陳小木")
        
        if st.button("➕ 確認租出（初始化行車數據）", type="primary"):
            if not rent_plate or not new_name:
                st.error("❌ 車牌與姓名不能為空！")
            else:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                # 使用 INSERT OR REPLACE：如果車牌存在就覆蓋租客並初始化數據，不存在就新增
                cursor.execute("""
                    INSERT OR REPLACE INTO cars (plate, name, speeding, braking, status, review_time) 
                    VALUES (?, ?, 0, 0, '待審核', '-')
                """, (rent_plate, new_name))
                conn.commit()
                conn.close()
                st.toast(f"🟢 {rent_plate} 已成功租出給 {new_name}！", icon="🚗")
                time.sleep(0.5)
                st.rerun()

    st.write("---")
    
    # 建立兩個區塊：左邊是「還車審核表單」，右邊是「還車結帳釋放系統」
    col_review, col_release = st.columns([1, 1])
    
    with col_review:
        st.write("### 🔍 1. 臨櫃選車與審核送出")
        # 篩選出目前有租客且尚未完成這次審核的車輛（或顯示全部供選擇）
        plate_options = ["請選擇車牌..."] + df_cars["車牌號碼"].tolist()
        selected_plate = st.selectbox("選擇要辦理還車審核的車牌：", plate_options)
        
        current_speeding, current_braking = 0, 0
        if selected_plate != "請選擇車牌...":
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT speeding, braking FROM cars WHERE plate = ?", (selected_plate,))
            row = cursor.fetchone()
            if row:
                current_speeding, current_braking = row[0], row[1]
            conn.close()

        with st.form(key="edge_data_form", clear_on_submit=False):
            st.write(f"📋 **當前操作車牌：{selected_plate if selected_plate != '請選擇車牌...' else '未選擇'}**")
            speeding = st.number_input("審核：超速次數 (0~50)", min_value=0, value=current_speeding)
            heavy_braking = st.number_input("審核：急煞次數 (0~50)", min_value=0, value=current_braking)
            submit_button = st.form_submit_button(label="🚀 打包密文與 ZKP 發送至雲端")
            
        if submit_button:
            if selected_plate == "請選擇車牌...":
                st.error("❌ 請先選擇正確的車牌號碼！")
            else:
                with st.spinner("正在進行加密與 ZKP 證明生成..."):
                    time.sleep(0.5)
                    pub_key, _ = paillier.generate_paillier_keypair()
                    
                    if 0 <= speeding <= 50 and 0 <= heavy_braking <= 50:
                        zkp_res, score_res = "Verified", (speeding * 10) + (heavy_braking * 5)
                    else:
                        zkp_res, score_res = "Failed", None
                    
                    st.session_state["db"] = {
                        "has_data": True,
                        "enc_speeding": str(pub_key.encrypt(speeding).ciphertext()),
                        "enc_braking": str(pub_key.encrypt(heavy_braking).ciphertext()),
                        "zkp_
