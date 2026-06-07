import streamlit as st
from phe import paillier
import time

st.set_page_config(page_title="跨平台 UBI 隱私聯防系統原型", page_icon="🛡️", layout="wide")
st.title("🛡️ 跨平台 UBI 隱私計算與零知識證明（ZKP）聯防系統")
st.write("本系統模擬分散式微服務架構，為方便現場 Demo 資料流，將三個獨立站點整合於統一決策面板呈現。")

# ==========================================
# 初始化跨分頁的共享記憶體 (模擬網路通訊暫存)
# ==========================================
if "db" not in st.session_state:
    st.session_state["db"] = {
        "has_data": False,
        "enc_speeding": None,
        "enc_braking": None,
        "zkp_status": "Waiting",
        "computed_score": None
    }

# ==========================================
# 建立網頁頂端的三個獨立站點分頁
# ==========================================
tab1, tab2, tab3 = st.tabs(["🚗 1. 租車平台端 (Edge)", "☁️ 2. 雲端計算大腦 (Cloud)", "🏢 3. 保險公司後台 (Core)"])

# ------------------------------------------
# 【分頁一：租車平台端】
# ------------------------------------------
with tab1:
    st.header("🚗 邊緣端駕駛數據採集與加密")
    st.info("模擬場景：用戶還車時，租車公司在本地 App/邊緣端直接將隱私數據加密，並生成 ZKP 範圍證明。")
    
    col1, col2 = st.columns(2)
    with col1:
        speeding = st.number_input("超速次數 (合法範圍: 0~50)", min_value=0, value=3, key="final_speed")
        heavy_braking = st.number_input("急煞次數 (合法範圍: 0~50)", min_value=0, value=5, key="final_brake")
    
    with col2:
        st.write("🔒 **邊緣端密碼學處理預覽：**")
        # 密碼學元件模擬
        pub_key, _ = paillier.generate_paillier_keypair()
        fake_enc = str(pub_key.encrypt(speeding).ciphertext())[:40] + "..."
        st.code(f"明文數據: {speeding} 次 $\rightarrow$ 同態密文: {fake_enc}", language="text")

    if st.button("🚀 打包密文與 ZKP 證明，發送至雲端大腦"):
        with st.spinner("正在進行非對稱同態加密與 ZKP 範圍證明生成..."):
            time.sleep(0.8) # 模擬運算延遲
            
            # ZKP 範圍證明檢查 (0~50次為合法駕駛行為)
            if 0 <= speeding <= 50 and 0 <= heavy_braking <= 50:
                zkp_res = "Verified"
                # 同態盲算權重模擬 (超速*10 + 急煞*5)
                score_res = (speeding * 10) + (heavy_braking * 5)
            else:
                zkp_res = "Failed"
                score_res = None
                
            # 將結果寫入共享記憶體 (模擬隔空丟包給雲端)
            st.session_state["db"] = {
                "has_data": True,
                "enc_speeding": str(pub_key.encrypt(speeding).ciphertext()),
                "enc_braking": str(pub_key.encrypt(heavy_braking).ciphertext()),
                "zkp_status": zkp_res,
                "computed_score": score_res
            }
        st.success("🎉 數據已成功進行密碼學打包，並透過 HTTPS 安全通道拋遞至雲端中心！請點擊切換至『2. 雲端計算大腦』分頁查看。")

# ------------------------------------------
# 【分頁二：雲端計算大腦】
# ------------------------------------------
with tab2:
    st.header("☁️ 中立雲端密文盲算中心")
    st.info("核心優勢：雲端平台自始至終**沒有解密私鑰**，也**看不到明文**，純粹在密文狀態下進行 ZKP 驗證與同態加法盲算。")
    
    db = st.session_state["db"]
    if db["has_data"]:
        st.success("🟢 【即時連線成功】偵測到來自租車平台端(Port 8501-Simulated)的加密封包！")
        
        c1, c2 = st.columns(2)
        with c1:
            st.warning("🔒 雲端接收到的原始密文數據流：")
            st.code(f"Enc_Speeding_Data: {db['enc_speeding'][:60]}...", language="text")
            st.code(f"Enc_Braking_Data:  {db['enc_braking'][:60]}...", language="text")
        
        with c2:
            st.info("🛡️ 零知識證明 (ZKP) 驗證閘門：")
            if db["zkp_status"] == "Verified":
                st.success("✅ ZKP 範圍證明驗證通過！證明該密文對應的明文在 [0~50] 合法區間內，未遭惡意竄改。")
                st.metric(label="雲端同態運算狀態", value="盲算完成，結果已轉發")
                st.caption("雲端已在不解密情況下，將超速與急煞密文進行同態加權疊加，並將全新的『總分密文』拋遞給保險公司。")
            else:
                st.error("🚨 警告：ZKP 範圍證明驗證失敗！檢測到該密文明文超出合規範圍（涉嫌惡意數據毒化攻擊）！")
                st.error("🛑 雲端安全防禦機制啟動：拒絕進行同態盲算，直接丟棄該封包，確保後台不受髒資料污染。")
    else:
        st.info("⏳ 目前雲端佇列無數據。請先在第一頁『租車平台端』輸入數據並點擊發送。")

# ------------------------------------------
# 【分頁三：保險公司後台】
# ------------------------------------------
with tab3:
    st.header("🏢 保險公司核心核保後台")
    st.info("隱私保護：保險公司獨家持有**解密私鑰**。它拿不到用戶詳細的每日行車軌跡明文，只能解密雲端算好的總分，用來決定最終費率。")
    
    db = st.session_state["db"]
    if db["has_data"] and db["zkp_status"] == "Verified" and db["computed_score"] is not None:
        st.success("🟢 成功接收由雲端盲算中心轉發的『風險總分密文』！")
        st.write("🔑 正在調用核心硬體安全模組 (HSM) 與私鑰進行最終解密...")
        
        # 觸發氣球特效
        st.balloons()
        
        score = db["computed_score"]
        st.metric(label="🛡️ 最終解密還原：用戶風險扣分總計", value=f"{score} 分")
        
        # 商業定價邏輯
        if score < 30:
            st.success("👑 精算費率等級：A (駕駛行為極佳，享有下期保費 8 折最優待！)")
        elif score < 70:
            st.info("ℹ️ 精算費率等級：B (駕駛行為正常，維持標準保費費率)")
        else:
            st.error("⚠️ 精算費率等級：C (高風險駕駛！觸發懲罰性條款，保費調漲 1.5 倍)")
            
    elif db["has_data"] and db["zkp_status"] == "Failed":
        st.error("❌ 無法取得精算總分：雲端因 ZKP 驗證失敗已攔截該次傳輸，保險公司未收到任何合法的盲算結果。")
    else:
        st.info("⏳ 等待雲端盲算中心拋遞最終的總分密文...")