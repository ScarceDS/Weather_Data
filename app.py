
import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import requests
import calendar
from io import StringIO
import pytz

st.set_page_config(layout="wide", page_title="NASA POWER Climate Dashboard")

st.title("🌍 NASA POWER - Climate Data Dashboard")
st.markdown("Compare weather parameters across multiple Saudi stations using NASA hourly data.")

@st.cache_data
def load_stations():
    return pd.read_excel("stations.xlsx")

stations_df = load_stations()
station_names = stations_df["Station Name"].tolist()
param_options = {
    "Temperature at 2m (°C)": "T2M",
    "Relative Humidity at 2m (%)": "RH2M",
    "Wind Speed at 10m (m/s)": "WS10M"
}
default_params = ["T2M"]
default_year = datetime.date.today().year - 1

st.sidebar.header("🔧 Filters")
selected_stations = st.sidebar.multiselect("Choose Stations", station_names, default=[station_names[0]])
selected_params = st.sidebar.multiselect("Select Parameters", list(param_options.keys()), default=param_options.keys())
start_date = st.sidebar.date_input("Start Date", datetime.date(default_year, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime.date.today() - datetime.timedelta(days=3))

tz_ksa = pytz.timezone("Asia/Riyadh")

@st.cache_data
def get_data(lat, lon, start, end, param):
    url = f"https://power.larc.nasa.gov/api/temporal/hourly/point"
    params = {
        "parameters": param,
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "CSV",
        "time-standard": "UTC"
    }
    for _ in range(10):
        try:
            res = requests.get(url, params=params, timeout=60)
            if res.status_code == 200:
                df = pd.read_csv(StringIO(res.text), skiprows=10)
                df["datetime"] = pd.to_datetime(df["YEAR"].astype(str) + df["MO"].astype(str).str.zfill(2) +
                                                df["DY"].astype(str).str.zfill(2) + df["HR"].astype(str).str.zfill(2),
                                                format="%Y%m%d%H", utc=True).dt.tz_convert(tz_ksa)
                return df.set_index("datetime")
        except:
            continue
    return None

if st.sidebar.button("🚀 Load & Analyze"):
    st.header("📈 Multi-station Parameter Analysis")
    for param_name in selected_params:
        param_code = param_options[param_name]
        st.subheader(f"🌀 {param_name}")
        fig = px.line()
        all_series = []
        for station in selected_stations:
            row = stations_df[stations_df["Station Name"] == station].iloc[0]
            df = get_data(row["Latitude"], row["Longitude"], start_date, end_date, param_code)
            if df is not None:
                df = df[[param_code]]
                df.columns = [f"{station}"]
                all_series.append(df)
                df_daily = df.resample("D").agg(["mean", "max", "min"]).droplevel(1, axis=1)
                df_daily["DOY"] = df_daily.index.dayofyear
                df_daily["Year"] = df_daily.index.year
                fig.add_scatter(x=df_daily.index, y=df_daily[station], mode="lines", name=station)
        st.plotly_chart(fig, use_container_width=True)

        # Day-of-Year Comparison
        if all_series:
            st.markdown("#### 📅 Day-of-Year Comparison")
            df_concat = pd.concat(all_series, axis=1)
            df_concat["DOY"] = df_concat.index.dayofyear
            df_concat["Year"] = df_concat.index.year
            for station in df_concat.columns[:-2]:
                fig2 = px.line(df_concat, x="DOY", y=station, color="Year", title=f"{station} - DOY Comparison")
                st.plotly_chart(fig2, use_container_width=True)

    # Optional: Export data section or advanced tabs (if required)

else:
    st.info("👈 Choose filters and click 'Load & Analyze' to begin.")
