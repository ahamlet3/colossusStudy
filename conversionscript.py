import geopandas as gpd
import pandas as pd

fips = ["13","12","17","26","36","37","39", "42", "47"]
for state_fips in fips:
    shp_path = f"./data/tracts/tl_2024_{state_fips}_tract/tl_2024_{state_fips}_tract.shp"
    pop_path = f"./data/tracts/tl_2024_{state_fips}_tract/population_{state_fips}.csv"

    tracts = gpd.read_file(shp_path)
    pop_df = pd.read_csv(pop_path)
    pop_df["GEOID"] = pop_df["GEOID"].astype(str).str.zfill(11)
    tracts["GEOID"] = tracts["GEOID"].astype(str)

    # Merge population into tracts
    merged = tracts.merge(pop_df, on="GEOID")

    # Export to GeoJSON
    
    merged.to_file(f"./data/tracts/tl_2024_{state_fips}_tract.geojson", driver="GeoJSON")
    print("exported a file")
