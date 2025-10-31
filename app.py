import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
from datetime import datetime, timedelta
import pytz

st.set_page_config(layout="wide")

stations_df = pd.read_excel("stations.xlsx")
stations = stations_df["Station Name"].tolist()
station_coords = stations_df.set_index("Station Name")[["Latitude", "Longitude"]].to_dict("index")

st.title("NASA Weather Dashboard")
st.markdown("Compare hourly weather data from multiple stations using NASA POWER API")

with st.sidebar:
    selected_stations = st.multiselect("Select Stations", stations, default=stations[:1])
    parameter = st.selectbox("Select Parameter", ["T2M", "RH2M", "PRECTOTCORR", "WS2M"])
    start_date = st.date_input("Start Date", datetime(2025, 10, 1))
    end_date = st.date_input("End Date", datetime.utcnow().date() - timedelta(days=3))
    run_button = st.button("Get Data")

@st.cache_data(show_spinner=False)
def fetch_nasa_data(lat, lon, param, start_date, end_date):
    url = (
        f"https://power.larc.nasa.gov/api/temporal/hourly/point?"
        f"parameters={param}&community=RE&latitude={lat}&longitude={lon}"
        f"&start={start_date}&end={end_date}&format=JSON&time-standard=UTC"
    )
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        values = data["properties"]["parameter"][param]
        df = pd.DataFrame(list(values.items()), columns=["datetime", param])
        df["datetime"] = pd.to_datetime(df["datetime"], format="%Y%m%d%H")
        df["datetime"] = df["datetime"].dt.tz_localize("UTC").dt.tz_convert("Asia/Riyadh").dt.tz_localize(None)
        return df
    else:
        return pd.DataFrame()

if run_button and selected_stations:
    all_data = []
    for station in selected_stations:
        coords = station_coords[station]
        df = fetch_nasa_data(coords["Latitude"], coords["Longitude"], parameter,
                             start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d"))
        if not df.empty:
            df["station"] = station
            all_data.append(df)

    if all_data:
        merged_df = pd.concat(all_data)

        tab1, tab2, tab3, tab4 = st.tabs(["📊 Time Series", "📈 Intra-Day", "📆 Intra-Month", "🗺️ Map"])

        with tab1:
            fig = px.line(merged_df, x="datetime", y=parameter, color="station", title="Hourly Time Series")
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            merged_df["hour"] = merged_df["datetime"].dt.hour
            hourly_avg = merged_df.groupby(["station", "hour"])[parameter].mean().reset_index()
            fig = px.line(hourly_avg, x="hour", y=parameter, color="station", title="Intra-Day Average (by Hour)")
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            merged_df["month"] = merged_df["datetime"].dt.month
            merged_df["day"] = merged_df["datetime"].dt.day
            fig = px.box(merged_df, x="day", y=parameter, color="station", animation_frame="month",
                         title="Intra-Month Distribution (animated by Month)")
            st.plotly_chart(fig, use_container_width=True)

        with tab4:
            map_df = pd.DataFrame([
                {"station": s, "lat": station_coords[s]["Latitude"], "lon": station_coords[s]["Longitude"]}
                for s in selected_stations
            ])
            st.map(map_df)

        st.download_button("📥 Download Data as CSV", merged_df.to_csv(index=False), file_name="weather_data.csv")
    else:
        st.warning("No data returned from NASA API.")




