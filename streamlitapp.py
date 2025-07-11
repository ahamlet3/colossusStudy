# streamlit_app.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import pydeck as pdk
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from matplotlib.colors import to_rgba

states = ["12", "13", "17", "26", "36", "37", "39", "42","47"]  # "06", "48",  FIPS codes

@st.cache_data
def load_tracts_and_pop():
    tracts_list = []
    for state in states:
        tracts_list.append(load_state_data(state))
    all_tracts = gpd.GeoDataFrame(pd.concat(tracts_list, ignore_index=True), crs=tracts_list[0].crs)
    all_tracts = all_tracts.to_crs(epsg=3857)
    return all_tracts

def load_state_data(state_fips):
    shp_path = f"./data/tracts/tl_2024_{state_fips}_tract/tl_2024_{state_fips}_tract.shp"
    pop_path = f"./data/tracts/tl_2024_{state_fips}_tract/population_{state_fips}.csv"

    tracts = gpd.read_file(shp_path)
    pop_df = pd.read_csv(pop_path)
    tracts["GEOID"] = tracts["GEOID"].astype(str)
    pop_df["GEOID"] = pop_df["GEOID"].astype(str).str.zfill(11)
    tracts = tracts.merge(pop_df, on="GEOID")
    return tracts


st.set_page_config(page_title="Colossus Risk Perception", layout="wide")
st.title("🧠 How Framing Affects Perceived Health Risk")
st.markdown("Context: This page explores the risk perception of the xAI datacenter called Colossus located a few miles from downtown Memphis, TN. ")
st.sidebar.header("🔍 Personalize Your Experience")
location_input = st.sidebar.text_input("Enter your city and state", value="3231 Riverport Rd, Memphis, TN 38109")
framing_mode = st.sidebar.radio("Choose framing style", ["Emotionally Framed", "Analytically Framed"])
# exposure_level = st.sidebar.selectbox("Have you heard of Colossus?", ["Never", "Somewhat", "Deeply aware"])
# health_status = st.sidebar.radio("Do you or someone in your household have asthma or a pollution-sensitive condition?", ["Yes", "No"])
st.sidebar.info("while the map works for any city or country, **population impact estimates** are only available for anywhere **within** the following 8 U.S. states:\n\n"
                    "- FL (Florida)"
                    "- GA (Georgia)\n"
                    "- IL (Illinois)\n"
                    "- MI (Michigan)\n"
                    "- NY (New York)\n"
                    "- NC (North Carolina)\n"
                    "- OH (Ohio)\n"
                    "- PA (Pennsylvania)\n"
                    "- TN (Tennessee)\n"
)
tracts = load_tracts_and_pop()

def calculate_risk(exposure, health):
    risk = 0.5
    if exposure == "Deeply aware":
        risk += 0.2
    elif exposure == "Somewhat":
        risk += 0.1
    if health == "Yes":
        risk += 0.2
    return min(risk, 1.0)

# perceived_risk = calculate_risk(exposure_level, health_status)

# Geocode with error handling
geolocator = Nominatim(user_agent="colossus_mapper", timeout=10)
try:
    location = geolocator.geocode(location_input)
except (GeocoderTimedOut, GeocoderServiceError):
    location = None

if location:
    user_lat, user_lon = location.latitude, location.longitude
else:
    st.warning("Geocoding failed or rate-limited. Defaulting to Memphis, TN.")
    user_lat, user_lon = 35.07, -90.06

city_point = Point(user_lon, user_lat)
city_point_proj = gpd.GeoSeries([city_point], crs="EPSG:4326").to_crs(epsg=3857).iloc[0]
# Create multiple distance buffers (2 km, 5 km, 10 km)
buffers = {
    "2 km": city_point_proj.buffer(2000),
    "5 km": city_point_proj.buffer(5000),
    "10 km": city_point_proj.buffer(10000)
}
for label, buffer in buffers.items():
    buffer_tracts = tracts[tracts.intersects(buffer)]
    popu = buffer_tracts["population"].sum()
    buffers[label] = {"buffer":buffer,"population":popu}


buffer_points = [
    {"lat": user_lat, "lon": user_lon, "radius": 2000, "color": [255, 51, 51, 60]},   # Red, semi-transparent
    {"lat": user_lat, "lon": user_lon, "radius": 5000, "color": [255, 204, 0, 40]},   # Yellow, more transparent
    {"lat": user_lat, "lon": user_lon, "radius": 10000, "color": [51, 204, 51, 40]}   # Green, very transparent
]

range_layers = []

for buff in buffer_points:
    range_layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=[buff],
            get_position='[lon, lat]',
            get_radius=buff["radius"],
            get_fill_color=buff["color"],
            pickable=False,
            stroked=False
        )
    )


if framing_mode == "Emotionally Framed":
    st.header("👧 Jasmine's Story")
    st.markdown("""
    Jasmine is 7 years old and lives in the Riverside neighborhood of Memphis, less than two kilometers from the Colossus data center.  
    She used to love riding her pink bike through the park near her home. But ever since Colossus began operating **35 gas turbines**, her life has changed.

    In the past year alone, Jasmine has been rushed to the ER **four times** for asthma attacks—**twice in the middle of the night**.  
    Her mom keeps an emergency inhaler in the kitchen, the car, and Jasmine’s backpack. On “red air” days, she can’t go outside at all.

    When Jasmine draws her family, she sometimes includes an oxygen mask over her face.  
    “She says the air burns her nose,” her mother explains.

    ---

    💬 *"It feels like I can't breathe when I try to run,"* Jasmine told her school nurse.  
    🩺 Her doctor warned: *"Children exposed to sustained NO₂ levels are at high risk of permanent lung damage."*

    ---

    This story is fictional—but grounded in real statistics from neighborhoods near major gas-powered data centers.

    """)
    st.info("Jasmine’s story is a lens through which we understand real impacts. This is **Affect Heuristic** in action—connecting data with lived human experience.")


else:
    st.header("📈 Public Health Summary")
    st.markdown("""
    Respiratory illness increases by 18–25% within 2 km of turbine sites. Colossus operates 35 natural gas turbines in a dense residential zone alongside various other powerplants and mills.
    Data from Memphis, TN shows a 45% higher asthma hospitalization rate than the TN average and Colossus can only attribute higher numbers.
    """)

colossus_lat, colossus_lon = 35.07, -90.06
# pollution_layer = pdk.Layer("ScatterplotLayer", data=[{"lat": colossus_lat, "lon": colossus_lon}], get_position='[lon, lat]', get_radius=2000, get_color='[255, 51, 51, 80]', pickable=True)
# marker_layer = pdk.Layer("ScatterplotLayer", data=[{"lat": colossus_lat, "lon": colossus_lon}], get_position='[lon, lat]', get_color='[255, 0, 0, 255]', get_radius=100, pickable=True)
user_marker_layer = pdk.Layer("ScatterplotLayer", data=[{"lat": user_lat, "lon": user_lon}], get_position='[lon, lat]', get_color='[0, 150, 255, 200]', get_radius=150, pickable=True)
user_pollution_layer = pdk.Layer("ScatterplotLayer", data=[{"lat": user_lat, "lon": user_lon}], get_position='[lon, lat]', get_radius=2000, get_color='[255, 51, 51, 60]', pickable=False)

# pdk.settings.mapbox_api_key = st.secrets["mapbox"]["mp_token"]
view_state = pdk.ViewState(latitude=user_lat, longitude=user_lon, zoom=12, pitch=0)


st.subheader("What If this was you right now?")
st.markdown("""
            Imagine Colossus in your backyard. The map below overlays the pollution risk zones of Colossus to any desired address. 
            In the sidebar, Enter your address or city to see how a 'Colossus' could affect your city. \n
            And remember... This isn't hypothetical. It's happening now. 
            """)
# 
# map_style="mapbox://styles/mapbox/dark-v11",  
# pollution_layer, marker_layer,user_pollution_layer, 
st.pydeck_chart(pdk.Deck(
    initial_view_state=view_state, 
    layers=[ user_marker_layer, range_layers], 
    tooltip={"text": f"Colossus Datacenter at {location_input}"}
    ))

st.markdown(f"""
**🗺️ Zone Legend & Population Estimates**  
🔴 **2 km radius** – High risk exposure zone : Population : {buffers["2 km"].get('population'):,.0f}  
🟡 **5 km radius** – Moderate risk exposure zone : Population : {buffers["5 km"].get('population'):,.0f}  
🟢 **10 km radius** – Lower but present risk exposure zone : Population : {buffers["10 km"].get('population'):,.0f}  
""")
with st.expander("📊 See More: Health Statistics About Gas Turbines"):
    st.markdown("""
                
    #### 🔍 Emissions & Power Comparison  
    **1** **5.** XAI began running 35 gas turbines without air pollution permits, exploiting a loophole that labels them "temporary". When asked, the Health Department granted a permit for only 15 turbines.
                
    **2.** Each Solar SMT130 is a 16.5 MW power plant. With 35 units, Colossus has a combined capacity of ~578 MW—equivalent to a mid‑to-large sized fossil fuel power station [(SMT Solutions)](https://www.solarturbines.com/en_US/solutions/applications/data-centers.html?)  
    
    **3.** "Children exposed to air pollution near natural gas infrastructure show a 30% increased risk of developing asthma before age 12." [(Long Term Asthma Study, 2017)](https://www.atsjournals.org/doi/10.1164/rccm.201706-1267OC)  

    **4.** Each 10 ppb increase in NO₂ exposure is linked to a 5.2% rise in all-cause mortality and a 27.5% increase in pneumonia deaths. [(Long-term NO2 Study)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7123874/)
        10 ppb of NO₂ is like 10 drops of ink in an Olympic-sized swimming pool — and yet it’s enough to raise your risk of dying from pneumonia by 27%. Colossus can exudes up to a 5-15 ppb increase of NO2 per day within the 2km range. 
                
    **5.** Shelby County (Memphis) consistently earns an “F” grade for ozone and smog levels from the American Lung Association
    
    **6.** The city’s Racial Dissimilarity Index is ~61, ranking it among the top 6 most racially segregated U.S. cities [(How-to Calculate Dissimilarity)](https://coascenters.howard.edu/dissimilarity-index-tutorial). Collectively, Memphis is ~61% Black and ~24% White. However, This isn’t isolated: Low-income, minority communities nationally bear disproportionate burdens—they are nearly 9× more likely to host toxic facilities
                """)


st.header("📣 Take Action Now")
st.markdown("""
Every child deserves clean air. If this issue moved you, take the next step. Don't wait for permission to protect your community. Talk to neighbors. Attend city council meetings. Demand transparency. Your voice is the first step to change.

*“We are now faced with the fact that tomorrow is today. We are confronted with the fierce urgency of now.”*
""")


st.header("Please submit a post-app survey!")
survey_url = "https://docs.google.com/forms/d/e/1FAIpQLScUMDGSQbrv0eUI9nswYN-RO5vqJH9ow8khBFBjnkuLXJ8p1A/viewform?usp=dialog"

st.markdown(f"""
    <a href="{survey_url}" target="_blank">
        <button style='padding: 10px 20px; font-size: 16px; border: none; border-radius: 5px; 
                       background-color: #4CAF50; color: white; cursor: pointer;'>
            📩 Take the Post-Model Survey
        </button>
    </a>
""", unsafe_allow_html=True)
