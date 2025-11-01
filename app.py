import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.express as px

# ------------------------------
# Load station list from Excel
# ------------------------------
@st.cache_data
def load_stations():
    df = pd.read_excel("stations.xlsx")
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
            return pd.DataFrame()

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
# Streamlit Layout
# ------------------------------
st.set_page_config(page_title="NASA Weather Dashboard", layout="wide")
st.title("NASA Weather Dashboard")
st.markdown("Compare hourly weather data from multiple stations using NASA POWER API")

# ------------------------------
# Sidebar Inputs
# ------------------------------
with st.sidebar:
    st.header("Station Settings")
    selected_stations = st.multiselect("Select Stations", stations_df["Station Name"].tolist(), default=["Riyadh"])
    selected_param = st.selectbox("Select Parameter", ["T2M", "RH2M", "WS10M"])

    today = datetime.today()
    start_date = st.date_input("Start Date", value=datetime(2016, 1, 1), min_value=datetime(2005, 1, 1))
    end_date = st.date_input("End Date", value=today - timedelta(days=3), max_value=today - timedelta(days=1))

    load_btn = st.button("📥 Load & Analyze Data")

# ------------------------------
# Main View
# ------------------------------
if load_btn:
    tab1, tab2 = st.tabs(["📊 Time Series", "📈 Max Daily Temp per Year"])

    # -------- Time Series Tab --------
    with tab1:
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
        st.subheader("📈 Hourly Time Series")
        st.plotly_chart(fig, use_container_width=True)

    # -------- Daily Max Tab --------
    with tab2:
        st.subheader("📊 Max Daily Temperature Comparison")
        daily_df_list = []

        for station in selected_stations:
            row = stations_df[stations_df["Station Name"] == station].iloc[0]
            df = fetch_hourly_weather_data(
                row["Latitude"], row["Longitude"],
                start_date.strftime("%Y%m%d"),
                end_date.strftime("%Y%m%d"),
                "T2M"
            )
            if not df.empty:
                df["date"] = df["datetime"].dt.date
                daily_max = df.groupby("date")["T2M"].max().reset_index()
                daily_max["year"] = pd.to_datetime(daily_max["date"]).dt.year
                daily_max["station"] = station
                daily_df_list.append(daily_max)

        if daily_df_list:
            merged = pd.concat(daily_df_list)
            fig2 = px.line(
                merged,
                x="date",
                y="T2M",
                color="year",
                line_group="station",
                facet_row="station",
                title="Max Daily Temperature by Year",
                labels={"T2M": "Max Temp (°C)", "date": "Date"}
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.warning("No daily max data found.")
