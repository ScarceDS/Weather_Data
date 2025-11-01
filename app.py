import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime, timedelta
import plotly.express as px

# ------------------------------
# Load station list from Excel
# ------------------------------
@st.cache_data
def load_stations():
    file_path = "stations.xlsx"
    df = pd.read_excel(file_path)
    return df[['Station Name', 'Latitude', 'Longitude']]

stations_df = load_stations()

# ------------------------------
# Fetch hourly weather data
# ------------------------------
def fetch_hourly_weather_data(lat, lon, start_date, end_date, parameter):
    url = (
        f"https://power.larc.nasa.gov/api/temporal/hourly/point"
        f"?parameters={parameter}&community=RE"
        f"&longitude={lon}&latitude={lat}&format=JSON"
        f"&start={start_date}&end={end_date}"
    )
    try:
        response = requests.get(url)
        data = response.json()

        if 'properties' not in data or 'parameter' not in data['properties']:
            return pd.DataFrame()  # empty dataframe

        hourly_data = data['properties']['parameter'][parameter]
        df = pd.DataFrame.from_dict(hourly_data, orient='index', columns=[parameter])
        df.index.name = 'datetime'
        df.reset_index(inplace=True)
        df['datetime'] = pd.to_datetime(df['datetime'], format="%Y%m%d%H")
        return df
    except Exception as e:
        st.error(f"API error: {e}")
        return pd.DataFrame()

# ------------------------------
# App UI
# ------------------------------
st.set_page_config(page_title="NASA Weather Dashboard", layout="wide")
st.title("NASA Weather Dashboard")
st.markdown("Compare hourly weather data from multiple stations using NASA POWER API")

# Tabs
tabs = st.tabs(["📊 Time Series", "📈 Intra-Day", "📅 Intra-Month", "🗺️ Map"])

with tabs[0]:  # Time Series
    selected_stations = st.multiselect("Select Stations", stations_df["Station Name"].tolist(), default=["Riyadh"])
    selected_param = st.selectbox("Select Parameter", ["T2M", "RH2M", "WS10M"])
    
    today = datetime.today()
    start_date = st.date_input("Start Date", value=datetime(2016, 1, 1), min_value=datetime(2005, 1, 1))
    end_date = st.date_input("End Date", value=today - timedelta(days=3), max_value=today - timedelta(days=1))

    if st.button("Get Data"):
        fig = px.line()
        for station in selected_stations:
            row = stations_df[stations_df["Station Name"] == station].iloc[0]
            df = fetch_hourly_weather_data(
                row["Latitude"], row["Longitude"],
                start_date.strftime("%Y%m%d"),
                end_date.strftime("%Y%m%d"),
                selected_param
            )
            if not df.empty:
                df["station"] = station
                fig.add_scatter(x=df["datetime"], y=df[selected_param], mode='lines', name=station)
            else:
                st.warning(f"No data found for {station}")
        st.plotly_chart(fig, use_container_width=True)
