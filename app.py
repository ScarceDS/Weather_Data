
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import calendar

@st.cache_data
def load_stations():
    df = pd.read_excel("stations.xlsx")
    return df[['Station Name', 'Latitude', 'Longitude']]

def fetch_nasa_data(lat, lon, start_date, end_date, parameter):
    url = f"https://power.larc.nasa.gov/api/temporal/hourly/point?parameters={parameter}&community=SB&longitude={lon}&latitude={lat}&start={start_date}&end={end_date}&format=JSON"
    try:
        df = pd.read_json(url)
        records = df['properties']['parameter'][parameter]
        df = pd.DataFrame(records).T
        df.index = pd.to_datetime(df.index)
        df.columns = [parameter]
        return df
    except:
        return pd.DataFrame()

def calculate_daily_stats(df, param):
    daily = df.resample('D').agg(['min', 'max', 'mean']).reset_index()
    daily.columns = ['date', 'Min', 'Max', 'Mean']
    daily['year'] = daily['date'].dt.year
    daily['dayofyear'] = daily['date'].dt.dayofyear
    return daily

def calculate_cdd_hdd(df, base_temp=18.3):
    daily = df.resample('D').mean().reset_index()
    daily['CDD'] = np.maximum(daily.iloc[:, 1] - base_temp, 0)
    daily['HDD'] = np.maximum(base_temp - daily.iloc[:, 1], 0)
    daily['year'] = daily['date'].dt.year
    daily['dayofyear'] = daily['date'].dt.dayofyear
    return daily

def plot_year_comparison(df, value_column, title):
    fig = px.line(df, x='dayofyear', y=value_column, color='year', markers=False, title=title)
    fig.update_layout(xaxis_title="Day of Year", yaxis_title=value_column)
    return fig

st.set_page_config(layout="wide")
st.sidebar.title("🛠 Filters")
stations_df = load_stations()

station_names = st.sidebar.multiselect("Choose Stations", stations_df['Station Name'].tolist())
parameters = st.sidebar.multiselect("Select Parameters", ['T2M', 'RH2M', 'WS2M', 'PRECTOTCORR', 'ALLSKY_SFC_SW_DWN'])
start_date = st.sidebar.date_input("Start Date", datetime(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime(2025, 10, 29))
st.sidebar.button("🚀 Load & Analyze")

page = st.sidebar.radio("Navigate", ["📊 Overview", "📈 Daily Max/Mean/Min", "📅 Yearly Comparison", "🔥 CDD/HDD Analysis"])

if station_names and parameters:
    for station in station_names:
        lat = stations_df.loc[stations_df['Station Name'] == station, 'Latitude'].values[0]
        lon = stations_df.loc[stations_df['Station Name'] == station, 'Longitude'].values[0]

        for param in parameters:
            df = fetch_nasa_data(lat, lon, start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d"), param)
            if df.empty:
                st.warning(f"No data available for {station} - {param}")
                continue

            if page == "📊 Overview":
                st.header(f"{station} - {param}")
                st.line_chart(df)

            elif page == "📈 Daily Max/Mean/Min":
                daily = calculate_daily_stats(df, param)
                fig = plot_year_comparison(daily, 'Max', f"{station} - Daily Max Temp")
                st.plotly_chart(fig, use_container_width=True)

            elif page == "📅 Yearly Comparison":
                daily = calculate_daily_stats(df, param)
                for col in ['Min', 'Max', 'Mean']:
                    fig = plot_year_comparison(daily, col, f"{station} - Daily {col}")
                    st.plotly_chart(fig, use_container_width=True)

            elif page == "🔥 CDD/HDD Analysis":
                daily = calculate_cdd_hdd(df)
                for col in ['CDD', 'HDD']:
                    fig = plot_year_comparison(daily, col, f"{station} - Daily {col}")
                    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Please select at least one station and one parameter to begin analysis.")
