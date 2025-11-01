
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta
import pytz

# Constants
PARAMETERS = {
    "Temperature (T2M)": "T2M",
    "Humidity (RH2M)": "RH2M",
    "Rainfall (PRECTOTCORR)": "PRECTOTCORR",
    "Wind Speed (WS10M)": "WS10M"
}
TIMEZONE = pytz.timezone("Asia/Riyadh")

# UI Layout
st.set_page_config(layout="wide", page_title="NASA POWER Climate Dashboard")
st.title("NASA POWER Climate Dashboard")
st.markdown("Analyze and visualize hourly weather data for multiple stations.")

# Sidebar Controls
with st.sidebar:
    st.header("User Input")
    stations_df = pd.read_excel("stations.xlsx")
    selected_stations = st.multiselect("Select Stations", options=stations_df["Station Name"].tolist())
    start_date = st.date_input("Start Date", value=datetime(2025, 1, 1))
    end_date = st.date_input("End Date", value=datetime.now(TIMEZONE).date() - timedelta(days=3))
    selected_parameters = st.multiselect("Select Parameters", options=list(PARAMETERS.keys()), default=list(PARAMETERS.keys()))
    trigger = st.button("Load & Analyze")

# Function to fetch data
@st.cache_data(show_spinner=False)
def fetch_nasa_power_data(lat, lon, start, end, param):
    url = (
        "https://power.larc.nasa.gov/api/temporal/hourly/point?"
        f"parameters={param}&community=RE&longitude={lon}&latitude={lat}"
        f"&start={start}&end={end}&format=JSON&time-standard=UTC"
    )
    retries = 3
    for _ in range(retries):
        try:
            response = requests.get(url, timeout=60)
            if response.ok:
                data = response.json()["properties"]["parameter"][param]
                df = pd.DataFrame.from_dict(data, orient="index", columns=[param])
                df.index = pd.to_datetime(df.index, format="%Y%m%d%H")
                df.index = df.index.tz_localize("UTC").tz_convert("Asia/Riyadh")
                return df
        except Exception:
            continue
    return pd.DataFrame()

def calculate_cdd_hdd(df, base_temp=18.0):
    df["CDD"] = (df["T2M"] - base_temp).clip(lower=0)
    df["HDD"] = (base_temp - df["T2M"]).clip(lower=0)
    return df

# Tabs Setup
if trigger:
    if not selected_stations or not selected_parameters:
        st.error("Please select at least one station and one parameter.")
    else:
        tab_titles = ["Overview", "Intra-day/Month", "Yearly Comparison", "Day-of-Year Trends", "CDD/HDD Analysis", "Raw Data"]
        tabs = st.tabs(tab_titles)

        raw_data_all = []
        for station in selected_stations:
            row = stations_df[stations_df["Station Name"] == station].iloc[0]
            station_id, name, lat, lon = row["ID"], row["Station Name"], row["Latitude"], row["Longitude"]

            station_data = pd.DataFrame()
            for label in selected_parameters:
                param_code = PARAMETERS[label]
                df = fetch_nasa_power_data(lat, lon, start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d"), param_code)
                if not df.empty:
                    station_data = station_data.join(df, how="outer")

            if not station_data.empty:
                station_data["Station"] = name
                station_data["Date"] = station_data.index
                station_data["Year"] = station_data.index.year
                station_data["Month"] = station_data.index.month
                station_data["Day"] = station_data.index.day
                station_data["Hour"] = station_data.index.hour
                station_data["DOY"] = station_data.index.dayofyear
                if "T2M" in station_data.columns:
                    station_data = calculate_cdd_hdd(station_data)
                raw_data_all.append(station_data)

        if not raw_data_all:
            st.error("No data retrieved.")
        else:
            df_all = pd.concat(raw_data_all)

            with tabs[0]:
                st.subheader("Overview")
                st.dataframe(df_all.head(100))

            with tabs[1]:
                st.subheader("Intra-day & Intra-month Analysis")
                fig = px.line(df_all, x="Hour", y=[c for c in df_all.columns if c in PARAMETERS.values()], color="Station")
                st.plotly_chart(fig, use_container_width=True)

            with tabs[2]:
                st.subheader("Yearly Comparison")
                for col in PARAMETERS.values():
                    if col in df_all.columns:
                        fig = px.box(df_all, x="Year", y=col, color="Station", title=f"Yearly Distribution of {col}")
                        st.plotly_chart(fig, use_container_width=True)

            with tabs[3]:
                st.subheader("Day-of-Year Trends")
                for col in PARAMETERS.values():
                    if col in df_all.columns:
                        fig = px.line(df_all, x="DOY", y=col, color="Year", facet_col="Station", title=f"{col} Trends by Day of Year")
                        st.plotly_chart(fig, use_container_width=True)

            with tabs[4]:
                st.subheader("CDD & HDD Analysis")
                cdd_fig = px.line(df_all, x="Date", y="CDD", color="Year", facet_col="Station", title="Daily CDD Comparison")
                hdd_fig = px.line(df_all, x="Date", y="HDD", color="Year", facet_col="Station", title="Daily HDD Comparison")
                st.plotly_chart(cdd_fig, use_container_width=True)
                st.plotly_chart(hdd_fig, use_container_width=True)

            with tabs[5]:
                st.subheader("Raw Data")
                st.dataframe(df_all)
                st.download_button("Download as CSV", df_all.to_csv(index=False), "weather_data.csv")
