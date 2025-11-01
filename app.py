import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import pytz
from datetime import datetime, timedelta
from utils import fetch_hourly_weather_data, calculate_cdd_hdd, load_stations
import os

st.set_page_config(layout="wide")

# -------------------------------------
# Load station data
# -------------------------------------
stations_df = load_stations("stations.xlsx")
stations_dict = dict(zip(stations_df["Station Name"], zip(stations_df["Latitude"], stations_df["Longitude"])))

# -------------------------------------
# Sidebar
# -------------------------------------
st.sidebar.title("Weather Data Explorer")
stations_selected = st.sidebar.multiselect("Select Stations", list(stations_dict.keys()), default=list(stations_dict.keys())[:1])

parameters = {
    "T2M": "Air Temperature at 2m (°C)",
    "RH2M": "Relative Humidity at 2m (%)",
    "WS2M": "Wind Speed at 2m (m/s)",
    "PRECTOTCORR": "Precipitation (mm/hr)"
}

parameter_selected = st.sidebar.selectbox("Select Parameter", list(parameters.keys()), format_func=lambda x: parameters[x])

# NASA supports data from 2001-01-01 to ~3 days before today
min_date = datetime(2001, 1, 1)
max_date = datetime.utcnow() - timedelta(days=3)

start_date = st.sidebar.date_input("Start Date", min_value=min_date, max_value=max_date, value=max_date - timedelta(days=365))
end_date = st.sidebar.date_input("End Date", min_value=min_date, max_value=max_date, value=max_date)

# -------------------------------------
# Title and Tabs
# -------------------------------------
st.markdown("""
    <h1 style='text-align: center; font-size: 36px;'>NASA Weather Dashboard</h1>
    <p style='text-align: center; color: gray;'>Compare hourly weather data from multiple stations using NASA POWER API</p>
    <hr>
""", unsafe_allow_html=True)

# Tabs
view = st.tabs(["📈 Time Series", "📉 Intra-Day", "📊 Intra-Month", "🗺️ Map"])

# -------------------------------------
# Fetch and process data
# -------------------------------------
if st.sidebar.button("Get Data"):
    all_data = []
    for station in stations_selected:
        lat, lon = stations_dict[station]
        df = fetch_hourly_weather_data(lat, lon, start_date, end_date, parameter_selected)
        if df is not None and not df.empty:
            df["station"] = station
            all_data.append(df)

    if not all_data:
        st.warning("No data returned for the selected parameters and stations.")
    else:
        weather_df = pd.concat(all_data)

        # Convert to Saudi local time (UTC+3)
        sa_tz = pytz.timezone("Asia/Riyadh")
        weather_df["datetime"] = pd.to_datetime(weather_df["datetime"])
        weather_df["datetime"] = weather_df["datetime"].dt.tz_localize("UTC").dt.tz_convert(sa_tz)

        # Time Series Tab
        with view[0]:
            fig = px.line(weather_df, x="datetime", y=parameter_selected, color="station", title="Hourly Time Series")
            st.plotly_chart(fig, use_container_width=True)
            st.download_button("📥 Download Data as CSV", weather_df.to_csv(index=False), file_name=f"weather_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")

        # Intra-Day Tab
        with view[1]:
            weather_df["hour"] = weather_df["datetime"].dt.hour
            intra_day = weather_df.groupby(["station", "hour"])[parameter_selected].mean().reset_index()
            fig_day = px.line(intra_day, x="hour", y=parameter_selected, color="station", markers=True, title="Intra-Day Average")
            st.plotly_chart(fig_day, use_container_width=True)

        # Intra-Month Tab
        with view[2]:
            weather_df["day"] = weather_df["datetime"].dt.day
            weather_df["month"] = weather_df["datetime"].dt.month
            monthly_stats = weather_df.groupby(["station", "month", "day"])[parameter_selected].mean().reset_index()
            fig_month = px.line(monthly_stats, x="day", y=parameter_selected, color="station", facet_col="month", facet_col_wrap=4,
                                title="Intra-Month Daily Averages")
            st.plotly_chart(fig_month, use_container_width=True)

        # Map Tab
        with view[3]:
            station_plot_df = stations_df[stations_df["Station Name"].isin(stations_selected)]
            fig_map = px.scatter_mapbox(station_plot_df, lat="Latitude", lon="Longitude", hover_name="Station Name",
                                        zoom=4, height=500)
            fig_map.update_layout(mapbox_style="open-street-map")
            st.plotly_chart(fig_map, use_container_width=True)

        # CDD and HDD
        cdd_hdd_df = calculate_cdd_hdd(weather_df, temp_column=parameter_selected)
        st.markdown("### Cooling & Heating Degree Days")
        st.dataframe(cdd_hdd_df)

else:
    st.info("Please select stations, parameter and date range then click 'Get Data'.")



