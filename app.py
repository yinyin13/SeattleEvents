import streamlit as st
import datetime
import pandas.io.sql as sqlio
import altair as alt
import pandas as pd
import folium
from streamlit_folium import st_folium

from db import conn_str

# Function to generate map based on DataFrame
def generate_map(df):
    m = folium.Map(location=[47.6062, -122.3321], zoom_start=12)
    for index, row in df.iterrows():
        folium.Marker([row['latitude'], row['longitude']], popup=row['venue']).add_to(m)
    return m

st.title("Seattle Events")

df = sqlio.read_sql_query("SELECT * FROM events", conn_str)

# Chart 1: Most Common Categories
st.altair_chart(
    alt.Chart(df).mark_bar().encode(x="count()", y=alt.Y("category").sort('-x')).interactive(),
    use_container_width=True,
)

# Chart 2: Most Popular Day of the Week
st.subheader("Number of Events by Day of the Week")
df['day_of_week'] = df['date'].dt.day_name()
day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
# Create a categorical data type with the specified order
cat_dtype = pd.CategoricalDtype(categories=day_order, ordered=True)
df['day_of_week'] = df['day_of_week'].astype(cat_dtype)
event_counts_by_day = df['day_of_week'].value_counts().sort_index()
st.bar_chart(event_counts_by_day)

# Controls
filtered_df = df.copy()

# Filter category
category = st.selectbox("Select a category", filtered_df['category'].unique())
filtered_df = filtered_df[filtered_df['category'] == category]

# Filter date
min_date = df['date'].min().date()
max_date = df['date'].max().date()
selected_date_range = st.date_input("Select date range", value=[min_date, max_date], min_value=min_date, max_value=max_date)
filtered_df = filtered_df[(filtered_df['date'].dt.date >= selected_date_range[0]) & (filtered_df['date'].dt.date <= selected_date_range[1])]

# Filter location
locations = ['All'] + list(df['location'].unique())
selected_location = st.selectbox("Select a location", options=locations)

if selected_location != 'All':
    filtered_df = filtered_df[filtered_df['location'] == selected_location]

# Filter weather condition
weather_conditions = ['All'] + list(df['short_forecast'].unique())
selected_weather_condition = st.selectbox("Select a weather condition", options=weather_conditions)

if selected_weather_condition != 'All':
    filtered_df = filtered_df[filtered_df['short_forecast'] == selected_weather_condition]

# Display filtered data
st.write(filtered_df)

# Update map based on filtered data
st.subheader("Event Locations")
st_folium(generate_map(filtered_df), width=1200, height=600)