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
