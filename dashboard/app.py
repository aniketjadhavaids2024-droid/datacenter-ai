import streamlit as st
import requests
import time

# Page config
st.set_page_config(
    page_title="DataCenter AI Dashboard",
    layout="wide"
)

# Title
st.title("⚡ Data Center AI Energy Optimization Dashboard")

# API URL
API_URL = "http://127.0.0.1:8000"

# Fetch data from API

def get_data():
    try:
        response = requests.get(f"{API_URL}/live")
        return response.json()
    except Exception:
        return None

data = get_data()

# If API not working
if data is None:
    st.error("❌ API not running. Start FastAPI server first.")
else:
    cpu = data.get("cpu")
    temp = data.get("temperature")
    energy = data.get("predicted_energy")
    suggestion = data.get("suggestion")

    # Metrics Row
    col1, col2, col3 = st.columns(3)
    col1.metric("🖥 CPU Usage (%)", cpu)
    col2.metric("🌡 Temperature (°C)", temp)
    col3.metric("⚡ Energy (kWh)", round(energy, 2) if energy is not None else None)

    # Suggestion Box
    st.subheader("💡 AI Suggestion")
    st.warning(suggestion)

    # Stats Section
    st.subheader("📊 System Stats")
    try:
        stats = requests.get(f"{API_URL}/stats").json()
        st.write(f"🔹 Average Energy: {round(stats.get('avg_energy', 0), 2)} kWh")
        st.write(f"🔹 Max Energy: {round(stats.get('max_energy', 0), 2)} kWh")
        st.write(f"🔹 Min Energy: {round(stats.get('min_energy', 0), 2)} kWh")
    except Exception:
        st.info("Stats endpoint not available")

    # History Section
    st.subheader("📈 Energy History")
    try:
        history = requests.get(f"{API_URL}/history").json()
        energy_values = [item.get("energy") for item in history if item.get("energy") is not None]
        st.line_chart(energy_values)
    except Exception:
        st.info("History endpoint not available")

    # Auto refresh every 3 sec
    time.sleep(3)
    st.rerun()
