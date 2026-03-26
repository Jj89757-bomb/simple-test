import streamlit as st
from pymsis import msis
st.title("Test succeed!")
import datetime

time = datetime.datetime(2023, 1, 1, 12)
lon = 0
lat = 45
alt = 400
data=msis.run(time,lon,lat,alt)
print(data)
