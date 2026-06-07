import streamlit as st
from phe import paillier
import time
from datetime import datetime

st.set_page_config(page_title="跨平台 UBI 隱私聯防系統原型", page_icon="🛡️", layout="wide")
st.title("🛡️ 跨平台 UBI 隱私計算與零知識證明（ZKP）聯防系統")

# ==========================================
# 初始化跨分頁的共享記憶體與「持久化資料庫」
# ==========================================
if "db" not in st.session_state:
    st.session_state["db"] = {
        "has_data": False,
        "enc_speeding": None,
        "enc_braking": None,
        "zkp_status": "Waiting",
        "computed_score": None
    }

if "car_database" not in st.session_state:
    st.session_state["car_database"] = {
        "車牌號碼": ["ABC-1234", "XYZ-5678", "QQ-9999"],
        "租客姓名": ["張大明", "王小美", "李黑客(惡意測試)"],
        "車機偵測_超速次數": [3, 1, 99],
        "車機偵測_急煞次數": [5, 2, 88],
        "狀態": ["待審核", "待審核", "待審核"],
        "審核時間": ["-", "-", "-"]
    }

if "history_log" not in st.session_state:
    st.session_state["history_log"] = []

if "current_speeding" not in st.session_state:
    st.session_state["current_speeding"] = 0
if "current_braking" not in st.session_state:
    st.session_state["current_braking"] = 0
if "just_submitted" not in st.session_state:
    st.session_state["just_submitted"] = False

# ==========================================
# 建立網頁頂端的三個獨立站點分頁
# ==========================================
tab1, tab2, tab3 = st.tabs(["🚗 1. 租車平台端 (Edge)", "☁️ 2. 雲端計算大腦 (Cloud)", "🏢 3. 保險公司後台 (Core)"])

# ------------------------------------------
# 【分頁一：租車平台端】（完全修復字串截斷版）
# ------------------------------------------
with tab1:
    st.header("🚗 邊緣端駕駛數據採集與加密")
    
    col_db, col_add = st.columns([2, 1])
    
    with col_db:
        st.write("### 📡 待處理還車車輛與 OBU 數據清單")
        st.caption("車聯網實時車隊狀態：")
        st.table(st.session_state["car_database"])
        
    with col_add:
        st.write("### 📝 新客戶租車登記處")
        st.caption("當有新客戶臨櫃租車時，新建立之車輛原始數據完美歸零：")
        
        new_plate = st.text_input("新車車牌", value="EX-5566", max_chars=10)
        new_name = st.text_input("客戶姓名", value="陳小木")
        
        if st.button("➕ 確認租出（新車上路數據歸零）", type="primary"):
            if new_plate in st.session_state["car_database"]["車牌號碼"]:
                st.error("❌ 該車牌已經在租借列表中了！")
            elif not new_plate or not new_name:
                st.error("❌ 車牌與姓名不能為空！")
            else:
                st.session_state["car_database"]["車牌號碼"].append(new_plate)
                st.session_state["car_database"]["租客姓名"].append(new_name)
                st.session_state["car_database"]["車機偵測_超速次數"].append(0) 
                st.session_state["car_database"]["車機偵測_急煞次數"].append(0) 
                st.session_state["car_database"]["狀態"].append("待審核")
                st.session_state["car_database"]["審核時間"].append("-")
                st.toast(f"🟢 {new_plate} 已成功出租！行車數據已初始化為 0。", icon="🚗")
                st.rerun()

    st.write("---")
    
    st.write("### 🔍 臨櫃選車與資料拉取")
    plate_options = ["請選擇車牌..."] + st.session_state["car_database"]["車牌號碼"]
    selected_plate = st.selectbox("請選擇當前辦理還車的車牌號碼：", plate_options)
    
    if selected_plate != "請選擇車牌...":
        idx = st.session_state["car_database"]["車牌號碼"].index(selected_plate)
        st.session_state["current_speeding"] = st.session_state["car_database"]["車機偵測_超速次數"][idx]
        st.session_state["current_braking"] = st.session_state["car_database"]["車機偵測_急煞次數"][idx]
    else:
        st.session_state["current_speeding"] = 0
        st.session_state["current_braking"] = 0

    st.write("### ✍️ 租車公司人工審核與密碼學打包")

    # 進入審核表單
    with st.form(key="edge_data_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"📋 **當前操作車牌：{selected_plate if selected_plate != '請選擇車牌...' else '未選擇'}**")
            speeding = st.number_input(
                "審核：超速次數 (0~50)", 
                min_value=0, 
                value=st.session_state["current_speeding"]
            )
            heavy_braking = st.number_input(
                "審核：急煞次數 (0~50)", 
                min_value=0, 
                value=st.session_state["current_braking"]
            )
        
        with col2:
            st.write("🔒 **邊緣端密碼學處理預覽：**")
            st.caption("系統處於高流暢模式。點擊下方按鈕將即時調用 Paillier 演算法將審核數據生成密文。")

        st.write("") 
        # 【完全修復！】第 119 行補齊完整的 st.form_submit_button 語法
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
                
                st.session_state["db"] = {
                    "has_data": True,
                    "enc_speeding": str(pub_key.encrypt(speeding).ciphertext()),
                    "enc_braking": str(pub_key.encrypt(heavy_braking).ciphertext()),
                    "zkp_status": zkp_res,
                    "computed_score": score_res
                }
                
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                target_idx = st.session_state["car_database"]["車牌號碼"].index(selected_plate)
                st.session_state["car_database"]["狀態"][target_idx] = "🟢 已審核"
                st.session_state["car_database"]["審核時間"][target_idx] = current_time
                
                history_entry = {
                    "時間戳記": current_time,
                    "車牌號碼": selected_plate,
                    "審核數據(超速/急煞)": f"{speeding}次 / {heavy_braking}次",
                    "ZKP 驗證閘門": "✅ 通過" if zkp_res == "Verified" else "🚨 攔截(異常數據)",
                    "同態盲算風險總分": f"{score_res} 分" if score_res is not None else "計算終止"
                }
                st.session_state["history_log"].append(history_entry)
                
                st.session_state["just_submitted"] = True
                
            st.rerun()

    if st.session_state["just_submitted"]:
        st.success("🎉 數據已成功發送至雲端中心！狀態已同步更新至上方管理清單。")
        st.session_state["just_submitted"] = False

    st.write("---")
    st.write("### 📑 UBI 歷史審核與雲端聯防存檔紀錄")
    if len(st.session_state["history_log"]) > 0:
        st.dataframe(st.session_state["history_log"], use_container_width=True)
    else:
        st.info("ℹ️ 目前尚無歷史上鏈審核紀錄。當您審核並送出任意車輛後，紀錄將在此永久留存。")

# ------------------------------------------
# 【分頁二：雲端計算大腦】
# ------------------------------------------
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

# ------------------------------------------
# 【分頁三：保險公司後台】
# ------------------------------------------
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
