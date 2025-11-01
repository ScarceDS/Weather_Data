
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
from io import BytesIO
import requests

st.set_page_config(page_title="NASA POWER - Climate Data Dashboard", layout="wide")

@st.cache_data
def load_stations():
    df = pd.read_excel("stations.xlsx")
    df = df.rename(columns=lambda x: x.strip())
    return df

def fetch_hourly_weather_data(lat, lon, start_date, end_date, parameter):
    base_url = "https://power.larc.nasa.gov/api/temporal/hourly/point"
    params = {
        "parameters": parameter,
        "community": "ag",
        "longitude": lon,
        "latitude": lat,
        "start": start_date.strftime('%Y%m%d'),
        "end": end_date.strftime('%Y%m%d'),
        "format": "JSON"
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        records = data["properties"]["parameter"][parameter]
        df = pd.DataFrame.from_dict(records, orient="index", columns=[parameter])
        df.index = pd.to_datetime(df.index)
        df = df.reset_index().rename(columns={"index": "datetime"})
        df["year"] = df["datetime"].dt.year
        df["month"] = df["datetime"].dt.month
        df["day"] = df["datetime"].dt.day
        df["hour"] = df["datetime"].dt.hour
        return df
    else:
        return pd.DataFrame()

def calculate_cdd_hdd(df, base_temp=18.0):
    df["date"] = df["datetime"].dt.date
    daily_avg = df.groupby("date")["T2M"].mean().reset_index()
    daily_avg["CDD"] = np.maximum(daily_avg["T2M"] - base_temp, 0)
    daily_avg["HDD"] = np.maximum(base_temp - daily_avg["T2M"], 0)
    daily_avg["year"] = pd.to_datetime(daily_avg["date"]).dt.year
    daily_avg["day_of_year"] = pd.to_datetime(daily_avg["date"]).dt.dayofyear
    return daily_avg

stations_df = load_stations()
station_names = stations_df["Station Name"].tolist()

st.sidebar.header("🛠️ Filters")
selected_stations = st.sidebar.multiselect("Choose Stations", station_names, default=["Riyadh"])
parameters_dict = {"T2M": "Temperature at 2m (°C)", "WS2M": "Wind Speed at 2m (m/s)", "RH2M": "Relative Humidity at 2m (%)"}
selected_params = st.sidebar.multiselect("Select Parameters", options=list(parameters_dict.keys()), default=["T2M"])
start_date = st.sidebar.date_input("Start Date", datetime(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime(2025, 10, 1))

if start_date > end_date:
    st.sidebar.error("End Date must be after Start Date.")

st.sidebar.button("🚀 Load & Analyze")

tabs = ["📊 Overview", "📈 Daily Max/Mean/Min", "📅 Yearly Comparison", "🔥 CDD/HDD Analysis", "🌤️ Peak & Seasons"]
selected_tab = st.sidebar.radio("Navigate", tabs, index=0)

@st.cache_data(show_spinner=False)
def load_all_data():
    all_data = {}
    for station in selected_stations:
        lat = stations_df[stations_df["Station Name"] == station]["Latitude"].values[0]
        lon = stations_df[stations_df["Station Name"] == station]["Longitude"].values[0]
        for param in selected_params:
            df = fetch_hourly_weather_data(lat, lon, start_date, end_date, param)
            if not df.empty:
                all_data[(station, param)] = df
    return all_data

data_cache = load_all_data()

def show_peak_and_season_tab():
    st.header("🌤️ Peak Daily & Seasonal Analysis")
    for (station, param), df in data_cache.items():
        st.subheader(f"📍 {station} - {parameters_dict.get(param, param)}")

        df["day_of_year"] = df["datetime"].dt.dayofyear
        df["year"] = df["datetime"].dt.year

        daily_max = df.groupby(["year", "day_of_year"])[param].max().reset_index()
        fig = px.line(daily_max, x="day_of_year", y=param, color="year", title=f"Peak Daily {param} Across Years")
        st.plotly_chart(fig, use_container_width=True)

        df["season"] = df["datetime"].dt.month % 12 // 3 + 1
        season_map = {1: "Winter", 2: "Spring", 3: "Summer", 4: "Fall"}
        df["season_name"] = df["season"].map(season_map)
        seasonal_avg = df.groupby(["year", "season_name"])[param].mean().reset_index()
        fig_season = px.bar(seasonal_avg, x="season_name", y=param, color="year", barmode="group",
                            title=f"Seasonal Average of {param} - {station}")
        st.plotly_chart(fig_season, use_container_width=True)

def show_tab(tab):
    if tab == "🌤️ Peak & Seasons":
        show_peak_and_season_tab()
    else:
        st.info("Other tabs' functionality can be implemented here.")

show_tab(selected_tab)
