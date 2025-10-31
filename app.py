import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime,timedelta

st.set_page_config(page_title="NASA POWER Dashboard", layout="wide")
st.title("🌍 NASA POWER - Interactive Weather Data Explorer (KSA Time)")

# ---- Sidebar (LEFT Panel) ----
st.sidebar.header("📊 خيارات التحليل")
stations = pd.read_excel("stations.xlsx")
station = st.sidebar.selectbox("اختر المحطة", stations["Station Name"])
param_key = st.sidebar.selectbox("اختر المتغير", ["T2M", "RH2M", "WS2M", "PRECTOTCORR"])
start_date = st.sidebar.date_input("تاريخ البداية", datetime(2025, 1, 1))
end_date = st.sidebar.date_input("تاريخ النهاية", datetime.today() - timedelta(days=3))

lat = stations[stations["Station Name"] == station]["Latitude"].values[0]
lon = stations[stations["Station Name"] == station]["Longitude"].values[0]
start = start_date.strftime("%Y%m%d")
end = end_date.strftime("%Y%m%d")

url = f"https://power.larc.nasa.gov/api/temporal/hourly/point?parameters=T2M&community=RE&latitude={lat}&longitude={lon}&start={start}&end={end}&format=JSON&time-standard=UTC"

@st.cache_data
def fetch_data(url):
    response = requests.get(url)
    data = response.json()
    records = data['properties']['parameter']['T2M']
    df = pd.DataFrame.from_dict(records, orient='index', columns=['T2M'])
    df.index = pd.to_datetime(df.index, format="%Y%m%d%H")
    df = df.tz_localize("UTC").tz_convert("Asia/Riyadh")
    df.reset_index(inplace=True)
    df.rename(columns={"index": "Datetime"}, inplace=True)
    return df

# ---- Main Analysis (RIGHT Panel) ----
col1, col2 = st.columns([1, 2])

with col2:
    try:
        df = fetch_data(url)
        st.success(f"تم تحميل {len(df)} صف من البيانات.")

        # حساب CDD و HDD
        df['CDD'] = df['T2M'].apply(lambda x: max(x - 18, 0))
        df['HDD'] = df['T2M'].apply(lambda x: max(18 - x, 0))

        # تحميل CSV
        st.download_button("💾 تحميل CSV", df.to_csv(index=False), file_name="weather_ksa.csv", mime="text/csv")

        # الرسم الزمني الكامل
        st.subheader("📈 تطور القيم عبر الزمن")
        st.plotly_chart(px.line(df, x="Datetime", y="T2M", title=f"درجة الحرارة - {station}"), use_container_width=True)

        # المتوسط اليومي
        df['Date'] = df['Datetime'].dt.date
        daily_avg = df.groupby("Date")["T2M"].mean().reset_index()
        st.subheader("📆 المتوسط اليومي")
        st.plotly_chart(px.bar(daily_avg, x="Date", y="T2M", title="المتوسط اليومي"), use_container_width=True)

        # CDD و HDD مجمعة يوميًا
        st.subheader("🌡️ CDD و HDD اليومية")
        daily_dd = df.groupby("Date")[["CDD", "HDD"]].sum().reset_index()
        st.plotly_chart(px.line(daily_dd, x="Date", y=["CDD", "HDD"], title="المتطلبات الحرارية اليومية"), use_container_width=True)

        # إحصائيات عامة
        st.subheader("🔢 إحصائيات عامة")
        st.dataframe(df[["T2M", "CDD", "HDD"]].describe().rename_axis("الوصف الإحصائي"))

        # خريطة تفاعلية للموقع
        st.subheader("🗺️ موقع المحطة على الخريطة")
        st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}))

    except Exception as e:
        st.error(f"حدث خطأ: {e}")
