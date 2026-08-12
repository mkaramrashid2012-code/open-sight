import os
import requests
import streamlit as st

API = os.getenv("OPENSIGHT_API", "http://127.0.0.1:8000/api/v1")
st.set_page_config(page_title="OpenSight Private", layout="wide")
st.title("OpenSight Private")
st.caption("Local video analytics dashboard")

try:
    health = requests.get(f"{API}/health", timeout=2).json()
    st.success(f"API: {health['status']}")
except requests.RequestException:
    st.error("API is not reachable. Start FastAPI first.")

st.header("Cameras")
if st.button("Refresh cameras"):
    st.rerun()
try:
    cameras = requests.get(f"{API}/cameras", timeout=3).json()
    for cam in cameras:
        with st.expander(cam["name"]):
            st.write({"id": cam["id"], "enabled": cam["enabled"], "RTSP": cam["rtsp_url"]})
except requests.RequestException:
    cameras = []

st.header("Search events")
object_class = st.text_input("Object class", placeholder="person")
min_conf = st.slider("Minimum confidence", 0.0, 1.0, 0.35)
if st.button("Search"):
    try:
        data = requests.post(f"{API}/search", json={"object_class": object_class or None, "min_confidence": min_conf}, timeout=10).json()
        st.dataframe(data, use_container_width=True)
    except requests.RequestException as exc:
        st.error(str(exc))
