
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
from io import StringIO
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title="NASA Weather Dashboard", layout="wide")

@st.cache_data
def load_stations():
    return pd.read_excel("stations.xlsx")

@st.cache_data
def fetch_weather_data(lat, lon, start_date, end_date, parameter):
    url = (
        f"https://power.larc.nasa.gov/api/temporal/hourly/point?"
        f"parameters={parameter}&community=RE&latitude={lat}&longitude={lon}"
        f"&start={start_date}&end={end_date}&format=CSV&time-standard=UTC"
    )
    while True:
        try:
            response = requests.get(url, timeout=20)
            if response.ok:
                df = pd.read_csv(StringIO(response.text), skiprows=10)
                df['TIMESTAMP'] = pd.to_datetime(df['YEAR'].astype(str) + df['MO'].astype(str).str.zfill(2) + df['DY'].astype(str).str.zfill(2) + df['HR'].astype(str).str.zfill(2), format='%Y%m%d%H', errors='coerce')
                df = df[['TIMESTAMP', parameter]].dropna()
                df = df.set_index('TIMESTAMP')
                df = df.tz_localize("UTC").tz_convert("Asia/Riyadh")
                df = df.reset_index()
                return df
        except Exception:
            continue

def calculate_cdd_hdd(df, base_temp=18.3):
    df["CDD"] = (df["T2M"] - base_temp).clip(lower=0)
    df["HDD"] = (base_temp - df["T2M"]).clip(lower=0)
    df["DATE"] = df["TIMESTAMP"].dt.date
    daily = df.groupby("DATE")[["CDD", "HDD"]].sum().reset_index()
    daily["Year"] = pd.to_datetime(daily["DATE"]).dt.year
    daily["DOY"] = pd.to_datetime(daily["DATE"]).dt.dayofyear
    return daily

# Sidebar filters
stations_df = load_stations()
st.sidebar.title("Filters")
station_names = st.sidebar.multiselect("Select Stations", stations_df["Station Name"].unique())
parameters = st.sidebar.multiselect("Select Parameters", ["T2M"], default=["T2M"])
today = datetime.now().date()
default_end = today - timedelta(days=3)
start_date = st.sidebar.date_input("Start Date", value=today.replace(month=1, day=1))
end_date = st.sidebar.date_input("End Date", value=default_end)

# Fetch and cache data
@st.cache_data
def load_all_data():
    all_data = {}
    for station in station_names:
        row = stations_df[stations_df["Station Name"] == station].iloc[0]
        lat, lon = row["Latitude"], row["Longitude"]
        for param in parameters:
            df = fetch_weather_data(lat, lon, start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d"), param)
            df["Station"] = station
            df["Parameter"] = param
            all_data[(station, param)] = df
    return all_data

data_cache = load_all_data()

# Main tabs
tab_titles = ["Overview", "Intra Day/Month", "Yearly Max Trends", "CDD & HDD Analysis", "Daily Year Comparison"]
tabs = st.tabs(tab_titles)

# === Overview Tab ===
with tabs[0]:
    st.header("Station Locations")
    fig = px.scatter_mapbox(stations_df[stations_df["Station Name"].isin(station_names)],
                            lat="Latitude", lon="Longitude", hover_name="Station Name",
                            zoom=4)
    fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)

# === Intra Day/Month ===
with tabs[1]:
    st.header("Intra Day and Intra Month Analysis")
    for key, df in data_cache.items():
        station, param = key
        df["Hour"] = df["TIMESTAMP"].dt.hour
        df["Month"] = df["TIMESTAMP"].dt.month
        st.subheader(f"{station} - {param}")
        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.box(df, x="Hour", y=param, title="Hourly Distribution")
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = px.box(df, x="Month", y=param, title="Monthly Distribution")
            st.plotly_chart(fig2, use_container_width=True)

# === Max Temp Trends ===
with tabs[2]:
    st.header("Daily Max Temperature Trends by Year")
    for key, df in data_cache.items():
        station, param = key
        df["Date"] = df["TIMESTAMP"].dt.date
        daily_max = df.groupby("Date")[param].max().reset_index()
        daily_max["Year"] = pd.to_datetime(daily_max["Date"]).dt.year
        daily_max["DOY"] = pd.to_datetime(daily_max["Date"]).dt.dayofyear
        fig = px.line(daily_max, x="DOY", y=param, color="Year", title=f"{station} - {param}")
        st.plotly_chart(fig, use_container_width=True)

# === CDD & HDD ===
with tabs[3]:
    st.header("Cooling and Heating Degree Days Comparison")
    for key, df in data_cache.items():
        station, param = key
        if param != "T2M":
            continue
        cdd_df = calculate_cdd_hdd(df)
        for metric in ["CDD", "HDD"]:
            fig = px.line(cdd_df, x="DOY", y=metric, color="Year", title=f"{station} - {metric}")
            st.plotly_chart(fig, use_container_width=True)

# === Yearly Comparison ===
with tabs[4]:
    st.header("Daily Value Comparison Across Years")
    for key, df in data_cache.items():
        station, param = key
        df["Date"] = df["TIMESTAMP"].dt.date
        df["Year"] = pd.to_datetime(df["Date"]).dt.year
        df["DOY"] = pd.to_datetime(df["Date"]).dt.dayofyear
        daily_avg = df.groupby(["Year", "DOY"])[param].mean().reset_index()
        fig = px.line(daily_avg, x="DOY", y=param, color="Year", title=f"{station} - Daily {param} Comparison")
        st.plotly_chart(fig, use_container_width=True)
