import folium
import requests
import json
import csv
import sys
import random

import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize, to_hex

def create_color_ramp(vmin, vmax, cmap_name):
    norm = Normalize(vmin, vmax)
    cmap = plt.colormaps[cmap_name]

    def get_color(value):
        value_clamped = max(min(value, vmax), vmin)
        rgba = cmap(norm(value_clamped))
        return to_hex(rgba)
    
    return get_color

nominatim_headers = {
    'User-Agent': 'HK-Election-Map',
}

def get_street_data(street_name, city):
    # base_url = "https://nominatim.openstreetmap.org/search"
    base_url = "http://localhost:8080/search"
    params = {
        'street': street_name,
        'city': city.replace("OT", ","),
        'country': 'Germany',
        'state': 'Niedersachsen',
        'osm_type': 'way',
        'format': 'jsonv2',
        'polygon_geojson': 1,
        'addressdetails': 1
    }
    
    response = requests.get(base_url, params=params, headers=nominatim_headers)
    data = response.json()
    
    if len(data) == 0 or data[0]["address"]["county"] != "Heidekreis":

        params = {
            # 'q': city.replace("OT", ","),
            'q': street_name,
            'format': 'jsonv2',
            'polygon_geojson': 1,
            'addressdetails': 1
        }
        response = requests.get(base_url, params=params, headers=nominatim_headers)
        data = response.json()


    if len(data) == 0 or data[0]["address"]["county"] != "Heidekreis":
        print("no relevant data found for", street_name, city)
        return None
    
    return data[0]



def get_streets_by_wahlbezirk_nr(ags: int, nr: int):
    streets = []
    with open("datasets/strassen_geo.json", 'r') as file:
        streets_data = json.loads(file.read())

    with open("datasets/strassen_to_wahlraum.csv", 'r') as file:
        reader = csv.DictReader(file, delimiter=",")
        for row in reader:
            if int(row["wahlbezirk_nr"]) == nr and int(row["ags"]) == ags:
                street = streets_data.get(f"{row['ort']}.{row['strasse']}")
                if street:
                    streets.append(street)
    return streets


def highlight_streets(m, streets, color, partei, wahlergebniss):    
    for street in streets:
        # Add the street geometry if available
        if street and 'geojson' in street:
            row = street["row"]
            tooltip = f"""{row['wahlbezirk_name']}<br>{row['strasse']}, {row['ort']}<br>
            {wahlergebniss[partei]/wahlergebniss["waehler"]:.2%} % {partei} ({wahlergebniss[partei]} / {wahlergebniss['waehler']} / {wahlergebniss["wahlberechtigte"]})
            """

            if partei == "wahlbeteiligung":
                tooltip = f"""{row['wahlbezirk_name']}<br>{row['strasse']}, {row['ort']}<br>
                {wahlergebniss["wahlbeteiligung"]:.2%} % Wahlbeteiligung ({wahlergebniss['waehler']} / {wahlergebniss["wahlberechtigte"]})
                """

            folium.GeoJson(
                street['geojson'],
                tooltip=tooltip,
                marker=folium.Circle(radius=200, fill_color=color, fill_opacity=0.4, color="black", weight=1),
                style_function=lambda x: {
                    'color': color,
                    'weight': 5,
                    'opacity': 0.8
                },
                
            ).add_to(m)
        else:
            print("no data for", street)
    
    # return m

def find_streets_no_data():
    new_streets_data = {}

    with open("datasets/strassen_geo.json", 'r') as file:
        streets_data = json.loads(file.read())

    with open("datasets/strassen_to_wahlraum.csv", 'r') as file:
        reader = csv.DictReader(file, delimiter=",")
        for row in reader:
            key = f"{row['ort']}.{row['strasse']}"
            if not streets_data.get(key):
                print(f"no data for {key}")
                data = get_street_data(row["strasse"], row["ort"])
                if data:
                    data["row"] = row
                    print(data)
                    new_streets_data[key] = data

    with open("datasets/strassen_geo.json", 'w') as file:
        file.write(json.dumps(streets_data | new_streets_data))

def get_wahlergebniss_by_wahlbezirk_nr(ags: int, nr: int):
    with open("datasets/wahlergebnisse_hk.csv", 'r') as file:
        reader = csv.DictReader(file, delimiter=",")
        for row in reader:
            if int(row["gebiet-nr"]) == nr and int(row["ags"]) == ags:
                waehler = int(row["B"])
                return {
                    "wahlberechtigte": int(row["A1"]),
                    "waehler": waehler,
                    "wahlbeteiligung": waehler / int(row["A1"]),
                    "spd": int(row["F1"]),
                    "cdu": int(row["F2"]),
                    "gruene": int(row["F3"]),
                    "fdp": int(row["F4"]),
                    "afd": int(row["F5"]),
                    "linke": int(row["F6"]),
                    "mensch_umwelt_tierschut": int(row["F7"]),
                    "basisdemokratische_partei_deutschland": int(row["F8"]),
                    "freie_waheler": int(row["F10"]),
                    "piratenpartei": int(row["F11"]),
                    "volt": int(row["F12"]),
                    "bsw": int(row["F16"]),
                    "row": row
                }

def get_all_bezirke():
    x = set()
    with open("datasets/wahlergebnisse_hk.csv", 'r') as file:
        reader = csv.DictReader(file, delimiter=",")
        for row in reader:
            if "Briefwahl" in row["gebiet-name"]:
                print("briefwahl, skip", row["gebiet-nr"])
                continue
            x.add((int(row["ags"]), int(row["gebiet-nr"])))

    return list(x)

find_streets_no_data()
# exit()

lon, lat = 9.585, 52.856
map = folium.Map(location=[lat, lon], zoom_start=15,
                 tiles = folium.TileLayer("cartodb dark_matter", overlay=True))

# Usage
# map_obj = highlight_street("Albrecht-Thaer-Straße", "Walsrode", "DE")

colors = [
    "#FF0000",  # Red
    "#00FF00",  # Lime Green
    "#0000FF",  # Blue
    "#FFFF00",  # Yellow
    "#FF00FF",  # Magenta
    "#00FFFF",  # Cyan
    "#FFA500",  # Orange
    "#800080",  # Purple
    "#008000",  # Dark Green
    "#000000"   # Black
]


# partei = "linke"
bezirke = get_all_bezirke()
# bezirke = [101]

parteien = [
    "wahlbeteiligung",
    "spd",
    "cdu",
    "gruene",
    "fdp",
    "afd",
    "linke",
    "mensch_umwelt_tierschut",
    "basisdemokratische_partei_deutschland",
    "freie_waheler",
    "piratenpartei",
    "volt",
    "bsw"
    ]

for partei in parteien:
    print("proecssing", partei)
    fg = folium.FeatureGroup(name=partei, show=(partei == "linke"), overlay=False).add_to(map)

    wahlergebnisse_relativ = []
    for b in bezirke:
        wahlergebniss = get_wahlergebniss_by_wahlbezirk_nr(*b)
        if partei == "wahlbeteiligung":
            wahlergebnisse_relativ.append(wahlergebniss["wahlbeteiligung"])
        else:
            wahlergebnisse_relativ.append(wahlergebniss[partei]/ wahlergebniss["waehler"])

    color_fn = create_color_ramp(min(wahlergebnisse_relativ), max(wahlergebnisse_relativ), cmap_name='pink')

    for bezirk in bezirke:
        wahlergebniss = get_wahlergebniss_by_wahlbezirk_nr(*bezirk)
        color = color_fn(wahlergebniss[partei]/wahlergebniss["waehler"])
        if partei == "wahlbeteiligung": color = color_fn(wahlergebniss["wahlbeteiligung"])
        name = wahlergebniss["row"]["gebiet-name"]

        highlight_streets(fg, get_streets_by_wahlbezirk_nr(*bezirk), color, partei, wahlergebniss)

folium.LayerControl().add_to(map)
print("creating file")

map.save("html/index.html")

# if map_obj:
    # map_obj.save("highlighted_street.html")


# streets_data = {}
# with open("datasets/strassen_to_wahlraum.csv", 'r') as file:
#     reader = csv.DictReader(file, delimiter=",")
#     for row in reader:
#         print(row["strasse"], row["ort"])
#         data = get_street_data(row["strasse"], row["ort"])
#         streets_data[f"{row['ort']}.{row['strasse']}"] = data
#
# with open("datasets/strassen_geo.json", 'w') as file:
#     file.write(json.dumps(streets_data))


