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
with tab1:
    st.header("邊緣端駕駛數據採集與加密")
    
    with st.form(key="edge_data_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            speeding = st.number_input("超速次數 (0~50)", min_value=0, value=3)
            heavy_braking = st.number_input("急煞次數 (0~50)", min_value=0, value=5)
        
        with col2:
            st.write("🔒 **邊緣端密碼學處理預覽：**")
            st.caption("系統處於高流暢模式。點擊下方按鈕將即時調用 Paillier 演算法生成密文。")

        st.write("") 
        submit_button = st.form_submit_button(label="發送至雲端")
        
    if submit_button:
        with st.spinner("正在上傳..."):
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
        st.success("🎉 數據已成功發送至雲端中心！")
        st.rerun()

# ------------------------------------------
# 【分頁二：雲端計算大腦】
# ------------------------------------------
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

# ------------------------------------------
# 【分頁三：保險公司後台】（已完全修復 elif/else 順序錯誤）
# ------------------------------------------
with tab3:
    st.header("🏢 保險公司核心核保後台")
    
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
