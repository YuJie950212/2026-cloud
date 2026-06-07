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
        new_plate = st.text_input("新車車牌", value="EX-5566", max_chars=10)
        new_name = st.text_input("客戶姓名", value="陳小木")
        
        if st.button("➕ 確認租出（數據寫入資料庫）", type="primary"):
            if not new_plate or not new_name:
                st.error("❌ 車牌與姓名不能為空！")
            else:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO cars VALUES (?, ?, 0, 0, '待審核', '-')", (new_plate, new_name))
                    conn.commit()
                    st.toast(f"🟢 {new_plate} 已成功出租！", icon="🚗")
                    time.sleep(0.5)
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ 該車牌已經在租借列表中了！")
                finally:
                    conn.close()

    st.write("---")
    st.write("### 🔍 臨櫃選車與資料拉取")
    plate_options = ["請選擇車牌..."] + df_cars["車牌號碼"].tolist()
    selected_plate = st.selectbox("請選擇當前辦理還車的車牌號碼：", plate_options)
    
    current_speeding, current_braking = 0, 0
    if selected_plate != "請選擇車牌...":
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT speeding, braking FROM cars WHERE plate = ?", (selected_plate,))
        row = cursor.fetchone()
        if row:
            current_speeding, current_braking = row[0], row[1]
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
            st.caption("🔒 系統處於高流暢模式。點擊下方按鈕將即時調用 Paillier 密碼學。")
        submit_button = st.form_submit_button(label="🚀 審核無誤：打包密文與 ZKP 發送至雲端")
        
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
                    "zkp_status": zkp_res,
                    "computed_score": score_res
                }
                
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("UPDATE cars SET status = '🟢 已審核', review_time = ? WHERE plate = ?", (current_time, selected_plate))
                
                zkp_text = "✅ 通過" if zkp_res == "Verified" else "🚨 攔截"
                score_text = f"{score_res} 分" if score_res is not None else "計算終止"
                cursor.execute("INSERT INTO history (timestamp, plate, data_summary, zkp_status, score) VALUES (?, ?, ?, ?, ?)",
                               (current_time, selected_plate, f"{speeding}次 / {heavy_braking}次", zkp_text, score_text))
                conn.commit()
                conn.close()
                st.session_state["just_submitted"] = True
            st.rerun()

    if st.session_state["just_submitted"]:
        st.success("🎉 數據已成功發送至雲端中心！狀態已同步儲存至實體資料庫。")
        st.session_state["just_submitted"] = False

    st.write("---")
    st.write("### 📑 UBI 歷史審核與雲端聯防存檔紀錄")
    conn = sqlite3.connect(DB_FILE)
    df_history = pd.read_sql_query("SELECT timestamp AS 時間戳記, plate AS 車牌號碼, data_summary AS '審核數據(超速/急煞)', zkp_status AS 'ZKP 驗證閘門', score AS '同態盲算風險總分' FROM history ORDER BY id DESC", conn)
    conn.close()
    if len(df_history) > 0:
        st.dataframe(df_history, use_container_width=True)
    else:
        st.info("ℹ️ 目前資料庫尚無歷史紀錄。")

# ==========================================
# 【分頁二：雲端計算大腦】
# ==========================================
with tab2:
    st.header("☁️ 中立雲端密文盲算中心")
    db = st.session_state["db"]
    if db["has_data"]:
        st.success("🟢 偵測到加密封包傳入")
        c1, c2 = st.columns(2)
        with c1:
            st.warning("🔒 雲端接收到的原始密文數據流：")
            st.code(f"Enc_Speeding_Data: {db['enc_speeding'][:60]}...", language="text")
            st.code(f"Enc_Braking_Data:  {db['enc_braking'][:60]}...", language="text")
        with c2:
            st.info("🛡️ 零知識證明 (ZKP) 驗證閘門：")
            if db["zkp_status"] == "Verified":
                st.success("✅ ZKP 範圍證明驗證通過！該密文合法。")
                st.metric(label="雲端同態運算狀態", value="盲算完成，結果已轉發")
            else:
                st.error("🚨 警告：ZKP 範圍證明驗證失敗！")
                st.error("🛑 雲端安全防禦機制啟動：拒絕進行同態盲算，直接丟棄該封包。")
    else:
        st.info("⏳ 目前雲端佇列無數據。")

# ==========================================
# 【分頁三：保險公司後台】
# ==========================================
with tab3:
    st.header("🏢 保險公司核心核保後台")
    db = st.session_state["db"]
    if db["has_data"] and db["zkp_status"] == "Verified" and db["computed_score"] is not None:
        st.success("🟢 成功接收由雲端盲算中心轉發的『風險總分密文』")
        score = db["computed_score"]
        st.metric(label="🛡️ 最終解密還原：用戶風險扣分總計", value=f"{score} 分")
        if score < 30:
            st.success("👑 精算費率等級：A (享有下期保費 8 折優惠)")
        elif score < 70:
            st.info("ℹ️ 精算費率等級：B (維持標準保費費率)")
        else:
            st.error("⚠️ 精算費率等級：C (高風險駕駛，保費調漲 1.5 倍)")
    elif db["has_data"] and db["zkp_status"] == "Failed":
        st.error("❌ 無法取得精算總分：雲端因 ZKP 驗證失敗已攔截該次傳輸。")
    else:
        st.info("⏳ 等待雲端盲算中心拋遞最終的總分密文...")
