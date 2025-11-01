import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# ---------- إعداد الواجهة ----------
st.set_page_config(page_title="NASA Weather Dashboard", layout="wide")
st.title("☀️ NASA Weather Dashboard")
st.markdown("تحميل بيانات الطقس من NASA POWER API (ساعية) لعدة محطات في السعودية")

# ---------- تحميل ملف المحطات ----------
stations_df = pd.read_excel("stations.xlsx")
station_names = stations_df["Station Name"].tolist()

# ---------- اختيار المحطة والمعامل ----------
selected_station = st.selectbox("📍 Select Station", station_names)
selected_param = st.selectbox("📊 Select Parameter", ["T2M", "RH2M", "PRECTOT", "WS10M"])

# ---------- اختيار الفترة الزمنية ----------
min_date = datetime(2015, 10, 1)
max_date = datetime(2035, 10, 1)
col1, col2 = st.columns(2)
start_date = col1.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
end_date = col2.date_input("End Date", value=max_date - timedelta(days=1), min_value=min_date, max_value=max_date)

# ---------- إحضار إحداثيات المحطة ----------
lat = stations_df.loc[stations_df["Station Name"] == selected_station, "Latitude"].values[0]
lon = stations_df.loc[stations_df["Station Name"] == selected_station, "Longitude"].values[0]

# ---------- دالة جلب البيانات من NASA POWER ----------
@st.cache_data(show_spinner=True)
def fetch_weather_data(lat, lon, start_date, end_date, parameter):
    url = (
        f"https://power.larc.nasa.gov/api/temporal/hourly/point?"
        f"start={start_date.strftime('%Y%m%d')}&end={end_date.strftime('%Y%m%d')}&"
        f"latitude={lat}&longitude={lon}&community=ag&parameters={parameter}&format=JSON"
    )
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    records = data["properties"]["parameter"][parameter]
    df = pd.DataFrame.from_dict(records, orient="index", columns=[parameter])
    df.index = pd.to_datetime(df.index)
    df.reset_index(inplace=True)
    df.rename(columns={"index": "datetime"}, inplace=True)
    return df

# ---------- تحميل البيانات عند الضغط ----------
if st.button("📥 Get Data"):
    df = fetch_weather_data(lat, lon, start_date, end_date, selected_param)
    if df is not None and not df.empty:
        st.success(f"تم تحميل البيانات ({len(df)} صف)")
        st.line_chart(df.set_index("datetime")[selected_param])
        st.download_button("📤 Download CSV", data=df.to_csv(index=False), file_name="weather_data.csv")
    else:
        st.error("⚠️ لم يتم تحميل البيانات، تأكد من التاريخ أو أعد المحاولة.")
