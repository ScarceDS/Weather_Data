import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import io
from datetime import datetime, timedelta
import pytz

# === Constants ===
TIMEZONE = 'Asia/Riyadh'
KSA_TZ = pytz.timezone(TIMEZONE)
NASA_BASE_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"
PARAMETERS = ["T2M", "T2M_MAX", "T2M_MIN", "RH2M", "PRECTOTCORR", "WS10M"]

# === Utility Functions ===
@st.cache_data
def load_station_data():
    df = pd.read_excel("stations.xlsx")
    df.columns = df.columns.str.strip()
    return df

@st.cache_data
def fetch_hourly_weather_data(lat, lon, start, end, parameter):
    url = (
        f"{NASA_BASE_URL}?parameters={parameter}"
        f"&community=RE&latitude={lat}&longitude={lon}"
        f"&start={start}&end={end}&format=JSON&time-standard=UTC"
    )
    while True:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            raw = response.json()
            data = raw["properties"]["parameter"][parameter]
            df = pd.DataFrame.from_dict(data, orient="index", columns=[parameter])
            df.index = pd.to_datetime(df.index, format="%Y%m%d%H").tz_localize("UTC").tz_convert(KSA_TZ)
            return df
        except Exception as e:
            st.warning(f"Retrying due to error: {e}")
            continue

def compute_cdd_hdd(df, base_temp=18.0):
    cdd = df["T2M"].apply(lambda x: max(0, x - base_temp))
    hdd = df["T2M"].apply(lambda x: max(0, base_temp - x))
    result = pd.DataFrame({"CDD": cdd, "HDD": hdd})
    result["Date"] = result.index.date
    return result.groupby("Date").sum()

# === UI ===
st.set_page_config(layout="wide", page_title="KSA Climate Dashboard")
st.title("Saudi Arabia Weather Analytics")
station_data = load_station_data()

with st.sidebar:
    st.header("Configuration")
    selected_stations = st.multiselect("Select Stations", options=station_data["Station Name"], default=station_data["Station Name"].iloc[0:1])
    parameters = st.multiselect("Select Parameters", options=PARAMETERS, default=["T2M"])
    end_date = datetime.now(KSA_TZ) - timedelta(days=3)
    start_date = st.date_input("Start Date", end_date - timedelta(days=30))
    end_date = st.date_input("End Date", end_date.date())

# === Data Loading ===
@st.cache_data
def load_all_data():
    results = {}
    start = pd.to_datetime(start_date).strftime("%Y%m%d")
    end = pd.to_datetime(end_date).strftime("%Y%m%d")
    for station in selected_stations:
        row = station_data[station_data["Station Name"] == station].iloc[0]
        station_results = {}
        for param in parameters:
            df = fetch_hourly_weather_data(row["Latitude"], row["Longitude"], start, end, param)
            station_results[param] = df
        results[station] = station_results
    return results

data_cache = load_all_data()
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Intra Day/Month", "Yearly Max Trends", "CDD/HDD Analysis", "Daily Year Comparison"])

# === Overview Tab ===
with tab1:
    st.subheader("Stations Map")
    station_map = station_data[station_data["Station Name"].isin(selected_stations)]
    fig_map = px.scatter_mapbox(
        station_map,
        lat="Latitude",
        lon="Longitude",
        hover_name="Station Name",
        zoom=4,
        height=500
    )
    fig_map.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

# === Intra Day/Month Tab ===
with tab2:
    st.subheader("Intra Day and Intra Month Analysis")
    for station in selected_stations:
        for param in parameters:
            df = data_cache[station][param].copy()
            df["Hour"] = df.index.hour
            df["Day"] = df.index.day
            df["Month"] = df.index.month

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Hourly Distribution** for {param} - {station}")
                st.plotly_chart(px.box(df, x="Hour", y=param, title="Hourly Distribution"), use_container_width=True)
            with col2:
                st.markdown(f"**Monthly Distribution** for {param} - {station}")
                st.plotly_chart(px.box(df, x="Month", y=param, title="Monthly Distribution"), use_container_width=True)

# === Yearly Max Trends Tab ===
with tab3:
    st.subheader("Daily Max Temperature Trends Across Years")
    for station in selected_stations:
        df = data_cache[station]["T2M"].copy()
        df = df.resample("D").max()
        df["Year"] = df.index.year
        df["DOY"] = df.index.dayofyear
        fig = px.line(df, x="DOY", y="T2M", color="Year", title=f"Max T2M Trends - {station}")
        st.plotly_chart(fig, use_container_width=True)

# === CDD/HDD Analysis Tab ===
with tab4:
    st.subheader("Cooling and Heating Degree Days")
    for station in selected_stations:
        df = data_cache[station]["T2M"].copy()
        result = compute_cdd_hdd(pd.DataFrame({"T2M": df}))
        result["Year"] = pd.to_datetime(result.index).year
        result["DOY"] = pd.to_datetime(result.index).dayofyear

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Daily CDD** - {station}")
            fig1 = px.line(result, x="DOY", y="CDD", color="Year", title="Cooling Degree Days")
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            st.markdown(f"**Daily HDD** - {station}")
            fig2 = px.line(result, x="DOY", y="HDD", color="Year", title="Heating Degree Days")
            st.plotly_chart(fig2, use_container_width=True)

# === Daily Year Comparison Tab ===
with tab5:
    st.subheader("Daily Comparison Across Years")
    for station in selected_stations:
        for param in parameters:
            df = data_cache[station][param].copy()
            df = df.resample("D").mean()
            df["Year"] = df.index.year
            df["DOY"] = df.index.dayofyear
            fig = px.line(df, x="DOY", y=param, color="Year", title=f"{param} Daily Mean Comparison - {station}")
            st.plotly_chart(fig, use_container_width=True)
