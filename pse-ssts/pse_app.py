from pydoc import classname

import pandas as pd
import dash_leaflet as dl
import dash_leaflet.express as dlx
import xml.etree.ElementTree as Xet
from dash_extensions.javascript import assign

from dash import Dash, html, dcc, Input, Output


# lib ***

def get_param(txt):
    p = txt.split(":")
    return p[1]


def load_data(filePath):
    rows = []
    xmlparse = Xet.parse(filePath)
    root = xmlparse.getroot()
    for row in root.iter('sst'):
        vls = row.get('vls')
        vl_splits = vls.split(',')
        vl_array = []
        for vl in vl_splits:
            if vl != '':
                vl_array.append(float(vl))
        vl_array.sort(reverse=True)
        vl_str = []
        for vl in vl_array:
            vlf = float(vl)
            vli = int(vl)
            svl = vli if vlf == vli else vlf
            vl_str.append(str(svl))
        rows.append({
            "desc": row.get('desc'),
            "geo": row.get('geo'),
            "name": row.get('name'),
            "lat": row.get('lat'),
            "lon": row.get('lon'),
            "path": row.get('path'),
            "vls": ', '.join(vl_str),
            "vl_750": True if (750 in vl_array) else False,
            "vl_400": True if (400 in vl_array) else False,
            "vl_220": True if (220 in vl_array) else False,
            "vl_110": True if (110 in vl_array) else False,
            "vl_20": True if (20 in vl_array) else False,
            "vl_15": True if (15 in vl_array) else False,
            "vl_10": True if (10 in vl_array) else False
        }
        )

    cols = ["desc", "geo", "name", "lat", "lon", "path", "vls", "vl_750", "vl_400", "vl_220", "vl_110", "vl_20",
            "vl_15", "vl_10"]
    return pd.DataFrame(rows, columns=cols)


def make_markers(ssts):
    markers = []
    for index, row in ssts.iterrows():
        markers.append(
            dict(name=row["name"], lat=row["lat"], lon=row["lon"], desc=row['desc'], vls=row['vls'])
        )
    return markers


# Data processing ***

all_ssts = load_data('db/pse-geo-ssts.xml')

# App Layout ***

tileLayer = dl.TileLayer()
layerControl = dl.LayersControl(
    [
        dl.BaseLayer(
            tileLayer,
            name="OpenStreetMaps",
            checked=True,
        ),
        dl.BaseLayer(
            dl.TileLayer(
                url="https://www.ign.es/wmts/mapa-raster?request=getTile&layer=MTN&TileMatrixSet=GoogleMapsCompatible&TileMatrix={z}&TileCol={x}&TileRow={y}&format=image/jpeg",
                attribution="IGN",
            ),
            name="IGN",
            checked=False,
        ),
    ])

stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]
app = Dash(__name__, external_stylesheets=stylesheets)

draw_marker = assign(
    """
        function(feature, latlng){
        const ic = L.icon({iconUrl: 'assets/icon.svg', iconSize: [24,24], iconAnchor: L.point(12, 22)});
        marker = new L.marker(latlng, {icon: ic});         
        return marker;
        }
    """
)

app.layout = html.Div(
    [
        html.Div(
            [
                dl.MapContainer(
                    children=[],
                    id="pse-map",
                    center=[52, 19],
                    zoom=6,
                    style={'height': '90vh'},
                ),
            ],
            className="row"
        ),
        html.Div(
            dcc.Checklist(
                id="vls_checklist",
                options=[
                    {'label': [html.Span('750 kV', style={'margin': '10px'})], 'value': 'vl_750'},
                    {'label': [html.Span('400 kV', style={'margin': '10px'})], 'value': 'vl_400'},
                    {'label': [html.Span('220 kV', style={'margin': '10px'})], 'value': 'vl_220'},
                    {'label': [html.Span('110 kV', style={'margin': '10px'})], 'value': 'vl_110'},
                ],
                value=[],
                inline=True,
                style={'textAlign': 'center'}
            ),
            className="row"
        ),
        html.Div(
            children=[
                html.Label(
                    id="stats",
                    children=["0 / 0"]
                )
            ],
            className="row",
            style={'textAlign': 'center'}
        )
    ]
)


# Callbacks ***
@app.callback([Output("pse-map", "children"),
               Output("stats", "children")],
              [Input("vls_checklist", "value")]
              )
def update_graph(chosen_value):
    # map
    final_filter = pd.Series(False, range(all_ssts.shape[0]))
    for cv in chosen_value:
        final_filter |= all_ssts[cv] == True

    ssts = all_ssts[final_filter]

    markers = make_markers(ssts)
    geojson = dlx.dicts_to_geojson(
        [{**c, **dict(tooltip="<h6><b>" + c['desc'] + "</b><br/>" + c['vls'] + "</h6>")}
         for c in markers])

    # stats
    stats = str(len(ssts)) + " / " + str(len(all_ssts))
    percentage = round(100 * len(ssts) / len(all_ssts), 1)

    return [
        [dl.GeoJSON(data=geojson, pointToLayer=draw_marker, cluster=True),
         layerControl
         ],
        stats + " (" + str(percentage) + "%)"
    ]


if __name__ == "__main__":
    app.run_server(debug=True)
