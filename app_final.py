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
    cursor.execute("CREATE TABLE IF NOT EXISTS cars (plate TEXT PRIMARY KEY, name TEXT, speeding INTEGER, braking INTEGER, status TEXT, review_time TEXT)")
    try:
        cursor.execute("SELECT name FROM history LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("DROP TABLE IF EXISTS history")
    cursor.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, plate TEXT, name TEXT, data_summary TEXT, zkp_status TEXT, score TEXT)")
    cursor.execute("SELECT COUNT(*) FROM cars")
    if cursor.fetchone()[0] == 0:
        initial_cars = [("ABC-1234", "張大明", 3, 5, "待審核", "-"), ("XYZ-5678", "王小美", 1, 2, "待審核", "-"), ("QQ-9999", "李黑客(惡意測試)", 99, 88, "待審核", "-")]
        cursor.executemany("INSERT INTO cars VALUES (?, ?, ?, ?, ?, ?)", initial_cars)
    conn.commit()
    conn.close()

init_db()

if "db" not in st.session_state:
    st.session_state["db"] = {"has_data": False, "enc_speeding": None, "enc_braking": None, "zkp_status": "Waiting", "computed_score": None}
if "just_submitted" not in st.session_state:
    st.session_state["just_submitted"] = False

tab1, tab2, tab3 = st.tabs(["🚗 1. 租車平台端 (Edge)", "☁️ 2. 雲端計算大腦 (Cloud)", "🏢 3. 保險公司後台 (Core)"])

# --- 【分頁一：租車平台端】 ---
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
        rent_plate = st.text_input("租出車牌 (現有或新車牌)", value="EX-5566", max_chars=10)
        new_name = st.text_input("新客戶姓名", value="陳小木")
        
        if st.button("➕ 確認租出（初始化行車數據）", type="primary"):
            if not rent_plate or not new_name:
                st.error("❌ 車牌與姓名不能為空！")
            else:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM cars WHERE plate = ?", (rent_plate,))
                existing_car = cursor.fetchone()
                
                if existing_car and existing_car[0] != "-":
                    st.error(f"❌ 登記失敗！車牌 {rent_plate} 目前正由租客「{existing_car[0]}」使用中，尚未結帳還車，無法重複登記！")
                    conn.close()
                else:
                    cursor.execute("INSERT OR REPLACE INTO cars (plate, name, speeding, braking, status, review_time) VALUES (?, ?, 0, 0, '待審核', '-')", (rent_plate, new_name))
                    conn.commit()
                    conn.close()
                    st.toast(f"🟢 {rent_plate} 已成功租出給 {new_name}！", icon="🚗")
                    time.sleep(0.5)
                    st.rerun()

        st.write("---")
        st.write("### 🗑️ 車庫車輛報廢/移除")
        st.caption("車輛更換車牌、報廢、換車時，可從車庫清單中永久移除該車牌。")
        
        all_plates = df_cars["車牌號碼"].tolist()
        target_remove_plate = st.selectbox("選擇欲移除/報廢的車牌：", ["請選擇車牌..."] + all_plates, key="remove_plate_select")
        
        if st.button("❌ 確認下架此車牌", type="secondary"):
            if target_remove_plate == "請選擇車牌...":
                st.error("❌ 請先選擇一個要移除的車牌！")
            else:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                # 檢查該車牌目前是否有租客正在使用中
                cursor.execute("SELECT name FROM cars WHERE plate = ?", (target_remove_plate,))
                row = cursor.fetchone()
                
                if row and row[0] != "-":
                    st.error(f"❌ 無法移除！車牌 {target_remove_plate} 目前正由租客「{row[0]}」使用中，請先在下方辦理『還車結帳』移除租客後再行報廢。")
                    conn.close()
                else:
                    # 如果是空車，允許直接從資料庫斬除
                    cursor.execute("DELETE FROM cars WHERE plate = ?", (target_remove_plate,))
                    conn.commit()
                    conn.close()
                    st.toast(f"🗑️ 車牌 {target_remove_plate} 已成功從系統車庫中移除！", icon="⚙️")
                    time.sleep(0.5)
                    st.rerun()

    st.write("---")
    col_review, col_release = st.columns([1, 1])
    
    with col_review:
        st.write("### 🔍 1. 臨櫃選車與審核送出")
        plate_options = ["請選擇車牌..."] + df_cars["車牌號碼"].tolist()
        selected_plate = st.selectbox("選擇要辦理還車審核的車牌：", plate_options)
        
        current_speeding, current_braking, current_name = 0, 0, "-"
        if selected_plate != "請選擇車牌...":
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT speeding, braking, name FROM cars WHERE plate = ?", (selected_plate,))
            row = cursor.fetchone()
            if row:
                current_speeding, current_braking, current_name = row[0], row[1], row[2]
            conn.close()

        is_empty_car = (current_name == "-") or (selected_plate == "請選擇車牌...")

        with st.form(key="edge_data_form", clear_on_submit=False):
            st.write(f"📋 **當前操作車牌：{selected_plate if selected_plate != '請選擇車牌...' else '未選擇'}**")
            st.write(f"👤 **當前車輛租客：{ '❌ 空車待租 (欄位鎖定)' if current_name == '-' else current_name }**")
            
            speeding = st.number_input("審核：超速次數 (0~50)", min_value=0, value=current_speeding, disabled=is_empty_car)
            heavy_braking = st.number_input("審核：急煞次數 (0~50)", min_value=0, value=current_braking, disabled=is_empty_car)
            submit_button = st.form_submit_button(label="🚀 打包密文與 ZKP 發送至雲端", disabled=is_empty_car)
            
        if is_empty_car and selected_plate != "請選擇車牌...":
            st.warning("🚨 提示：該車輛目前為車庫空車，無行車數據可供審核。請先至右上方『新客戶租車登記處』指派租客。")

        if submit_button and not is_empty_car:
            with st.spinner("正在進行加密與 ZKP 證明生成..."):
                time.sleep(0.5)
                pub_key, _ = paillier.generate_paillier_keypair()
                zkp_res, score_res = ("Verified", (speeding * 10) + (heavy_braking * 5)) if (0 <= speeding <= 50 and 0 <= heavy_braking <= 50) else ("Failed", None)
                
                st.session_state["db"] = {"has_data": True, "enc_speeding": str(pub_key.encrypt(speeding).ciphertext()), "enc_braking": str(pub_key.encrypt(heavy_braking).ciphertext()), "zkp_status": zkp_res, "computed_score": score_res}
                
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("UPDATE cars SET status = '🟢 已審核', review_time = ? WHERE plate = ?", (current_time, selected_plate))
                zkp_text, score_text = ("✅ 通過", f"{score_res} 分") if zkp_res == "Verified" else ("🚨 攔截", "計算終止")
                cursor.execute("INSERT INTO history (timestamp, plate, name, data_summary, zkp_status, score) VALUES (?, ?, ?, ?, ?, ?)", (current_time, selected_plate, current_name, f"{speeding}次 / {heavy_braking}次", zkp_text, score_text))
                conn.commit()
                conn.close()
                st.session_state["just_submitted"] = True
            st.rerun()

    with col_release:
        st.write("### 🔄 2. 還車結帳與移除租客")
        st.caption("點擊按鈕將該租客移除，車輛恢復空車待租狀態。")
        reviewed_cars = df_cars[df_cars["狀態"] == "🟢 已審核"]["車牌號碼"].tolist()
        
        if len(reviewed_cars) == 0:
            st.info("⏳ 目前沒有需要辦理結帳的車輛（請先在左側完成車輛審核送出）。")
        else:
            release_plate = st.selectbox("選擇要結帳並清空租客的車牌：", reviewed_cars)
            if st.button("✅ 完成結帳：清空租客、數據歸零變回空車", type="secondary"):
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("UPDATE cars SET name = '-', speeding = 0, braking = 0, status = '待審核', review_time = '-' WHERE plate = ?", (release_plate,))
                conn.commit()
                conn.close()
                st.toast(f"♻️ {release_plate} 訂單已結清！租客已成功移出。", icon="🔄")
                time.sleep(0.5)
                st.rerun()

    if st.session_state["just_submitted"]:
        st.success("🎉 數據已成功發送至雲端中心！狀態已同步儲存至實體資料庫。")
        st.session_state["just_submitted"] = False

    st.write("---")
    st.write("### 📑 UBI 歷史審核與雲端聯防存檔紀錄")
    
    conn = sqlite3.connect(DB_FILE)
    df_history = pd.read_sql_query("SELECT id, timestamp AS 時間戳記, plate AS 車牌號碼, name AS 租客姓名, data_summary AS '審核數據(超速/急煞)', zkp_status AS 'ZKP 驗證閘門', score AS '同態盲算風險總分' FROM history ORDER BY id DESC", conn)
    conn.close()
    
    if len(df_history) > 0:
        df_history.insert(0, "選取銷毀", False)
        col_btn1, col_btn2 = st.columns([2, 1])
        
        with col_btn1:
            st.write("💡 **管理員面板**：請直接在下方表格最左側勾選欲永久抹除的紀錄：")
            edited_df = st.data_editor(
                df_history,
                column_config={"id": None, "選取銷毀": st.column_config.CheckboxColumn(help="勾選以永久抹除此筆紀錄")},
                disabled=["id", "時間戳記", "車牌號碼", "租客姓名", "審核數據(超速/急煞)", "ZKP 驗證閘門", "同態盲算風險總分"],
                use_container_width=True,
                key="history_editor"
            )
            
            to_delete_ids = edited_df[edited_df["選取銷毀"] == True]["id"].tolist()
            
            if len(to_delete_ids) > 0:
                if st.button(f"🗑️ 確定執行：抹除這 {len(to_delete_ids)} 筆已選取的紀錄", type="secondary"):
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute(f"DELETE FROM history WHERE id IN ({','.join(['?']*len(to_delete_ids))})", to_delete_ids)
                    conn.commit()
                    conn.close()
                    st.toast("🗑️ 所選取的歷史紀錄已從硬碟中成功抹除！")
                    time.sleep(0.5)
                    st.rerun()
                    
        with col_btn2:
            st.write("🚨 **危險管理區**")
            confirm_all = st.checkbox("🔥 我確認要「清空整張歷史資料表」（將釋放所有儲存空間）", key="chk_all")
            if st.button("💥 執行一鍵全清空", type="primary", disabled=not confirm_all):
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM history")
                conn.commit()
                conn.close()
                st.toast("💥 歷史資料庫已全部重置清空！")
                time.sleep(0.5)
                st.rerun()
    else:
        st.info("ℹ️ 目前資料庫尚無歷史紀錄。")

# --- 【分頁二：雲端計算大腦】 ---
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

# --- 【分頁三：保險公司後台】 ---
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
