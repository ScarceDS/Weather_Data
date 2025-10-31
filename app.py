# Streamlit NASA Weather Data App with Multiple Station Comparison, CDD/HDD, and KSA Time Support

import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
import io

st.set_page_config(layout="wide")
st.title("NASA Weather Data Explorer")

# Load stations
stations_df = pd.read_excel("stations.xlsx")
stations_df = stations_df.dropna(subset=["Latitude", "Longitude"])

# Sidebar controls
with st.sidebar:
    st.header("User Input")
    selected_stations = st.multiselect("Select Stations", stations_df["Station Name"], default=stations_df["Station Name"].iloc[:2])
    start_date = st.date_input("Start Date", datetime.utcnow() - timedelta(days=30))
    end_date = st.date_input("End Date", datetime.utcnow() - timedelta(days=3))
    parameter = st.selectbox("Parameter", ["T2M", "T2M_MAX", "T2M_MIN", "RH2M", "PRECTOTCORR", "WS2M"])
    submit = st.button("Fetch Data")

# Convert UTC to KSA
def to_ksa_time(utc_dt):
    ksa = pytz.timezone("Asia/Riyadh")
    return utc_dt.replace(tzinfo=pytz.utc).astimezone(ksa)

# Fetch data function
def fetch_data(lat, lon, start, end, param):
    base = "https://power.larc.nasa.gov/api/temporal/hourly/point"
    url = f"{base}?parameters={param}&community=RE&latitude={lat}&longitude={lon}&start={start}&end={end}&format=JSON&time-standard=UTC"
    while True:
        try:
            res = requests.get(url)
            res.raise_for_status()
            json_data = res.json()
            records = json_data["properties"]["parameter"][param]
            df = pd.DataFrame.from_dict(records, orient="index", columns=[param])
            df.index = pd.to_datetime(df.index)
            df = df.tz_localize("UTC").tz_convert("Asia/Riyadh")
            df[param] = df[param].astype(float)
            return df
        except Exception as e:
            st.warning(f"Retrying due to error: {e}")

# Main Execution
if submit and selected_stations:
    tabs = st.tabs(["Data", "Charts", "CDD/HDD", "Map"])
    combined = pd.DataFrame()

    with tabs[0]:
        st.subheader("Combined Data Table")

    with tabs[1]:
        fig_temp = go.Figure()

    with tabs[2]:
        st.subheader("Cooling & Heating Degree Days")
        cdd_fig, hdd_fig = go.Figure(), go.Figure()

    with tabs[3]:
        st.subheader("Station Locations")
        m = px.scatter_mapbox(
            stations_df[stations_df["Station Name"].isin(selected_stations)],
            lat="Latitude", lon="Longitude", text="Station Name",
            zoom=4, height=500
        )
        m.update_layout(mapbox_style="open-street-map")
        st.plotly_chart(m, use_container_width=True)

    for station in selected_stations:
        row = stations_df[stations_df["Station Name"] == station].iloc[0]
        df = fetch_data(row.Latitude, row.Longitude, start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d'), parameter)
        df = df.rename(columns={parameter: station})

        # Merge
        if combined.empty:
            combined = df.copy()
        else:
            combined = combined.join(df, how="outer")

        # Intra-day analysis
        intra = df.copy()
        intra["Hour"] = intra.index.hour
        avg_hourly = intra.groupby("Hour")[station].mean().reset_index()
        fig_temp.add_trace(go.Scatter(x=avg_hourly["Hour"], y=avg_hourly[station], mode='lines', name=station))

        # CDD/HDD
        cdd = (df[station] - 18).clip(lower=0).resample("D").sum()
        hdd = (18 - df[station]).clip(lower=0).resample("D").sum()
        cdd_fig.add_trace(go.Scatter(x=cdd.index, y=cdd, name=station))
        hdd_fig.add_trace(go.Scatter(x=hdd.index, y=hdd, name=station))

    with tabs[0]:
        st.dataframe(combined)
        csv = combined.to_csv().encode('utf-8')
        st.download_button("Download CSV", csv, file_name="nasa_weather_data.csv", mime="text/csv")

    with tabs[1]:
        st.plotly_chart(fig_temp, use_container_width=True)

    with tabs[2]:
        st.plotly_chart(cdd_fig, use_container_width=True)
        st.plotly_chart(hdd_fig, use_container_width=True)
else:
    st.info("Select inputs from the sidebar to begin.")
