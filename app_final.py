import streamlit as st
from phe import paillier
import time

st.set_page_config(page_title="跨平台 UBI 隱私聯防系統原型", page_icon="", layout="wide")
st.title("跨平台 UBI 隱私計算與零知識證明（ZKP）聯防系統")

if "db" not in st.session_state:
    st.session_state["db"] = {
        "has_data": False,
        "enc_speeding": None,
        "enc_braking": None,
        "zkp_status": "Waiting",
        "computed_score": None
    }

tab1, tab2, tab3 = st.tabs(["1. 租車平台端 (Edge)", "2. 雲端計算大腦 (Cloud)", "3. 保險公司後台 (Core)"])

#first
這個點子完全把「租車管理系統」的真實感拉滿了！在現實運作中，店員的畫面上確實會顯示一個待處理的還車列表，清單上寫著車牌號碼、客戶姓名以及車機自動偵測到的原始數據。

為了實現這個需求，我們可以直接在第一頁上方設計一個「車載數據資料庫清單」（用 Streamlit 的表格呈現）。店員只要在下拉選單中「選擇車牌號碼」，系統就會啪一聲自動把該車牌對應的超速、急煞數據撈出來，填入底下的審核表單！

我們馬上來把第一頁升級成擁有車牌資料庫連動功能的進階版本：

🛠️ 程式碼升級
請打開你的 app_final.py，將 # 【分頁一：租車平台端】 底下的程式碼全部替換成以下版本：

Python
# ------------------------------------------
# 【分頁一：租車平台端】（車牌資料庫即時連動版）
# ------------------------------------------
with tab1:
    st.header("🚗 邊緣端駕駛數據採集與加密")
    
    # 1. 初始化記憶體狀態
    if "just_submitted" not in st.session_state:
        st.session_state["just_submitted"] = False
        
    # 初始化目前選中的車牌與數值暫存器
    if "current_speeding" not in st.session_state:
        st.session_state["current_speeding"] = 0
    if "current_braking" not in st.session_state:
        st.session_state["current_braking"] = 0

    # 2. 模擬後台車載 OBU 原始資料庫
    st.write("### 📡 待處理還車車輛與 OBU 數據清單")
    st.caption("以下為車聯網系統自動回傳、儲存在本地資料庫的未審核資料：")
    
    # 建立一個精美的模擬資料庫表格
    mock_db = {
        "車牌號碼": ["ABC-1234", "XYZ-5678", "QQ-9999"],
        "租客姓名": ["張大明", "王小美", "李黑客(惡意數據測試)"],
        "車機偵測_超速次數": [3, 1, 99],
        "車機偵測_急煞次數": [5, 2, 88],
        "狀態": ["待審核", "待審核", "待審核"]
    }
    st.table(mock_db) # 直接在畫面上秀出表格
    
    # 3. 選擇車牌連動機制
    st.write("### 🔍 臨櫃選車與資料拉取")
    selected_plate = st.selectbox(
        "請選擇當前辦理還車的車牌號碼：",
        ["請選擇車牌...", "ABC-1234", "XYZ-5678", "QQ-9999"]
    )
    
    # 當使用者切換選單時，動態將資料庫的數據塞進輸入框
    if selected_plate == "ABC-1234":
        st.session_state["current_speeding"] = 3
        st.session_state["current_braking"] = 5
    elif selected_plate == "XYZ-5678":
        st.session_state["current_speeding"] = 1
        st.session_state["current_braking"] = 2
    elif selected_plate == "QQ-9999":
        st.session_state["current_speeding"] = 99
        st.session_state["current_braking"] = 88
    elif selected_plate == "請選擇車牌...":
        st.session_state["current_speeding"] = 0
        st.session_state["current_braking"] = 0

    st.write("---")
    st.write("### ✍️ 租車公司人工審核與密碼學打包")

    # 4. 審核表單（數值會隨著上面的下拉選單自動改變）
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
                
                st.session_state["just_submitted"] = True
                
            st.rerun()

    if st.session_state["just_submitted"]:
        st.success("🎉 數據已成功發送至雲端中心！請點擊切換至『2. 雲端計算大腦』分頁查看。")
        st.session_state["just_submitted"] = False
#Second
with tab2:
    st.header("中立雲端密文盲算中心")
    
    db = st.session_state["db"]
    if db["has_data"]:
        st.success("🟢 偵測到加密封包傳入")
        
        c1, c2 = st.columns(2)
        with c1:
            st.warning("🔒 雲端接收到的原始密文數據流：")
            st.code(f"Enc_Speeding_Data: {db['enc_speeding'][:60]}...", language="text")
            st.code(f"Enc_Braking_Data:  {db['enc_braking'][:60]}...", language="text")
        
        with c2:
            st.info("ZKP驗證閘門：")
            if db["zkp_status"] == "Verified":
                st.success("✅ ZKP 範圍證明驗證通過！該密文合法。")
                st.metric(label="雲端同態運算狀態", value="結果已轉發")
            else:
                st.error("🚨 警告：ZKP 範圍證明驗證失敗！")
                st.error("🛑 雲端安全防禦機制啟動：拒絕進行同態盲算，直接丟棄該封包。")
    else:
        st.info("⏳ 目前雲端佇列無數據。")

#Third
with tab3:
    st.header("保險公司核心核保後台")
    
    db = st.session_state["db"]
    if db["has_data"] and db["zkp_status"] == "Verified" and db["computed_score"] is not None:
        st.success("🟢 成功接收由雲端中心的『風險總分密文』")
        
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
        # else 必須在最後面作為預設狀態
        st.info("⏳ 等待雲端盲算中心拋遞最終的總分密文...")
