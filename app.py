import streamlit as st
import pandas as pd
import requests
import datetime as dt
from io import StringIO
import plotly.express as px

# ---------------------- الإعدادات العامة ---------------------- #
st.set_page_config(page_title="NASA Weather Dashboard", layout="wide")
st.title("🌤 NASA Weather Dashboard")
st.write("Compare hourly weather data from multiple stations using NASA POWER API")

# ---------------------- إعدادات الإدخال ---------------------- #
stations = {
    "Riyadh": (24.7136, 46.6753),
    "Jeddah": (21.4858, 39.1925),
    "Dammam": (26.4207, 50.0888),
    "Makkah": (21.3891, 39.8579),
    "Madinah": (24.5247, 39.5692),
    "Turaif": (31.6729, 38.6636),
}

parameters = {
    "T2M": "Air Temperature at 2 Meters (°C)",
    "RH2M": "Relative Humidity at 2 Meters (%)",
    "WS2M": "Wind Speed at 2 Meters (m/s)",
}

# ---------------------- دوال الأدوات ---------------------- #
def fetch_hourly_weather_data(lat, lon, start_date, end_date, parameter):
    url = (
        f"https://power.larc.nasa.gov/api/temporal/hourly/point"
        f"?start={start_date}&end={end_date}&latitude={lat}&longitude={lon}"
        f"&parameters={parameter}&community=RE&format=CSV"
    )

    response = requests.get(url)
    if response.status_code != 200:
        st.error(f"API request failed: {response.status_code}")
        return pd.DataFrame()

    raw_data = StringIO(response.text)
    df = pd.read_csv(raw_data, skiprows=10)

    df = df.rename(columns={"YEAR": "year", "MO": "month", "DY": "day", "HR": "hour", parameter: "value"})
    df["datetime"] = pd.to_datetime(
        df[["year", "month", "day", "hour"]], errors="coerce"
    )
    df = df.dropna(subset=["datetime"])
    df = df[["datetime", "value"]]
    return df

def calculate_cdd_hdd(df, base_temp=18.0):
    df["CDD"] = (df["value"] - base_temp).clip(lower=0)
    df["HDD"] = (base_temp - df["value"]).clip(lower=0)
    return df

# ---------------------- واجهة المستخدم ---------------------- #
st.sidebar.header("Select Stations")
selected_stations = st.sidebar.multiselect("Select Stations", options=stations.keys(), default=["Riyadh"])

st.sidebar.header("Select Parameter")
selected_param = st.sidebar.selectbox("Select Parameter", options=list(parameters.keys()), index=0)

min_date = dt.date(2005, 10, 1)
max_date = dt.date(2035, 10, 1)

start_date = st.sidebar.date_input("Start Date", min_value=min_date, max_value=max_date, value=min_date)
end_date = st.sidebar.date_input("End Date", min_value=min_date, max_value=max_date, value=dt.date(2025, 10, 29))

if start_date > end_date:
    st.sidebar.error("Start date must be before end date.")
else:
    if st.sidebar.button("Get Data"):
        all_data = []
        for station in selected_stations:
            lat, lon = stations[station]
            df = fetch_hourly_weather_data(
                lat,
                lon,
                start_date.strftime("%Y%m%d"),
                end_date.strftime("%Y%m%d"),
                selected_param,
            )
            if not df.empty:
                df["station"] = station
                df = calculate_cdd_hdd(df)
                all_data.append(df)

        if all_data:
            combined_df = pd.concat(all_data)
            st.subheader("📈 Hourly Time Series")
            fig = px.line(combined_df, x="datetime", y="value", color="station", title=parameters[selected_param])
            st.plotly_chart(fig, use_container_width=True)

            st.download_button("⬇️ Download Data as CSV", combined_df.to_csv(index=False), file_name="weather_data.csv")

            # Optional: CDD/HDD plotting
            if "CDD" in combined_df.columns:
                st.subheader("Cooling Degree Days (CDD)")
                fig_cdd = px.line(combined_df, x="datetime", y="CDD", color="station")
                st.plotly_chart(fig_cdd, use_container_width=True)

                st.subheader("Heating Degree Days (HDD)")
                fig_hdd = px.line(combined_df, x="datetime", y="HDD", color="station")
                st.plotly_chart(fig_hdd, use_container_width=True)
        else:
            st.warning("No data retrieved. Please try different parameters or date ranges.")








