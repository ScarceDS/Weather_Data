import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="NASA POWER Dashboard", layout="wide")
st.title("🌍 NASA POWER - Interactive Weather Data Explorer")

stations = pd.read_excel("stations.xlsx")
station = st.selectbox("اختر المحطة", stations["Station Name"])
param_key = st.selectbox("اختر المتغير", ["T2M", "RH2M", "WS2M", "PRECTOTCORR"])
start_date = st.date_input("تاريخ البداية", datetime(2025, 1, 1))
end_date = st.date_input("تاريخ النهاية", datetime.today())

lat = stations[stations["Station Name"] == station]["Latitude"].values[0]
lon = stations[stations["Station Name"] == station]["Longitude"].values[0]
start = start_date.strftime("%Y%m%d")
end = end_date.strftime("%Y%m%d")

url = f"https://power.larc.nasa.gov/api/temporal/hourly/point?parameters={param_key}&community=RE&latitude={lat}&longitude={lon}&start={start}&end={end}&format=JSON&time-standard=UTC"

@st.cache_data
def fetch_data():
    response = requests.get(url)
    data = response.json()
    records = data['properties']['parameter'][param_key]
    df = pd.DataFrame.from_dict(records, orient='index', columns=[param_key])
    df.index = pd.to_datetime(df.index, format="%Y%m%d%H")
    df.reset_index(inplace=True)
    df.rename(columns={"index": "Datetime"}, inplace=True)
    return df

try:
    df = fetch_data()
    st.success(f"تم تحميل {len(df)} صف من البيانات.")
    st.download_button("📥 تحميل CSV", df.to_csv(index=False), file_name="weather.csv", mime="text/csv")
    st.line_chart(df.set_index("Datetime")[param_key])
except Exception as e:
    st.error(f"حدث خطأ: {e}")
