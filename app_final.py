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
# 【分頁一：租車平台端】（完全修復表單按鈕縮進版）
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

    # 這裡所有的程式碼都完美鎖在表單 inside
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
        # 按鈕對齊完美包在 form 之中
        submit_button = st.form_submit_
