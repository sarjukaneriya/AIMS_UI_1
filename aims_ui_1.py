import os
import re
import random
import string
import sqlite3
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, State
from flask import Flask, send_from_directory
import plotly.express as px

# Set up paths
STATIC_DIR = "./static"
DB_FILE = "pi.db"
EXCEL_FILE = "Activity_Summary.xlsx"

# Ensure static directory exists
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# Function to process video files
def process_video_files():
    pattern = r'(\d{4}-\d{2}-\d{2})_(\d{4})_(\d{4}-\d{2}-\d{2})_(\d{4})_(\w+-\w+)\.mp4'
    
    data = []
    
    for file_name in os.listdir(STATIC_DIR):
        matches = re.findall(pattern, file_name)
        if matches:
            start_date, start_time, end_date, end_time, vehicle_id = matches[0]
            total_hours = (int(end_time) - int(start_time)) / 100.0
            data.append({
                "Date": start_date,
                "Start Time": f"{start_time[:2]}:{start_time[2:]}",
                "End Time": f"{end_time[:2]}:{end_time[2:]}",
                "Total Activity Hours": total_hours,
                "Location": "220-PROD-B23",
                "Personnel Count": random.randint(1, 10),
                "JON #": ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)),
                "Vehicle ID": vehicle_id,
                "Notes": "",
                "File Name": file_name
            })

    df = pd.DataFrame(data)
    df.to_excel(EXCEL_FILE, index=False)
    return df

# Setup SQLite database
def setup_database(df):
    conn = sqlite3.connect(DB_FILE)
    df.to_sql('activity', conn, if_exists='replace', index=False)
    conn.close()

# Process files and setup database
df = process_video_files()
setup_database(df)

# Initialize Flask and Dash
server = Flask(__name__)
app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Load data from SQLite
conn = sqlite3.connect(DB_FILE)
df = pd.read_sql("SELECT * FROM activity", conn)
conn.close()

# Create Graph
def create_figure(data):
    fig = px.line(data, x="Date", y="Total Activity Hours", markers=True,
                  title="Activity Hours Over Time",
                  line_shape="spline", template="simple_white")
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="#f9f9f9",
        plot_bgcolor="#f9f9f9",
        font=dict(color="#333", size=12)
    )
    return fig

# Create the Dashboard Layout
app.layout = dbc.Container(fluid=True, children=[
    # Navbar
    dbc.Navbar(
        dbc.Container([
          html.A([
                dbc.Col(html.Img(src="/assets/1.png", height="40px"), width="auto", className="d-flex align-items-center"),
                dbc.Col(html.H2("AIMS: Activity Dashboard", className="ms-3"), width="auto", className="d-flex align-items-center",style={ "color":"#6c757d"})
            ], href="/", className="d-flex align-items-center",style={"text-decoration":"none"})
        ], fluid=True, className="g-0 d-flex"),
        color="light",
        dark=False,
        sticky="top",
        style={"padding": "10px", "boxShadow": "0 2px 4px rgba(0,0,0,0.1)"}
    ),

    # Filters and Graphs
    dbc.Row([
        dbc.Col([
            html.H4("Filters", className="text-center text-dark mt-4"),
            dcc.Dropdown(
                id="date_filter",
                options=[{"label": d, "value": d} for d in df["Date"].unique()],
                multi=True,
                placeholder="Select Date...",
                style={"background-color": "#ffffff", "color": "#333"}
            ),
            dcc.Dropdown(
                id="vehicle_filter",
                options=[{"label": v, "value": v} for v in df["Vehicle ID"].unique()],
                multi=True,
                placeholder="Select Vehicle...",
                style={"background-color": "#ffffff", "color": "#333", "marginTop": "10px"}
            ),
            html.Button("Reset", id="reset_button", className="btn btn-secondary mt-3", n_clicks=0),
        ], width=3, style={"background-color": "#f1f1f1", "padding": "20px", "borderRadius": "10px"}),

        dbc.Col([
            dcc.Graph(id="activity_graph", figure=create_figure(df))
        ], width=9),
    ], className="mt-4"),

    # Data Table
    dbc.Row([
        dbc.Col([
            html.H4("Activity Log", className="text-dark mt-4"),
            dash_table.DataTable(
                id="data_table",
                columns=[{"name": i, "id": i} for i in df.columns],
                data=df.to_dict("records"),
                page_size=10,
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": "#e1e1e1",
                    "color": "#333",
                    "fontWeight": "bold"
                },
                style_cell={
                    "backgroundColor": "#ffffff",
                    "color": "#333",
                    "padding": "10px",
                    "textAlign": "left"
                },
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#f9f9f9'}
                ]
            )
        ], width=12),
    ], className="mt-4"),

], style={"background-color": "#f8f8f8", "padding-bottom": "30px"})

# Callbacks
@app.callback(
    Output("data_table", "data"),
    Output("activity_graph", "figure"),
    Input("date_filter", "value"),
    Input("vehicle_filter", "value"),
    Input("reset_button", "n_clicks")
)
def update_data(date_val, vehicle_val, reset_click):
    dff = df.copy()

    if date_val:
        dff = dff[dff["Date"].isin(date_val)]
    if vehicle_val:
        dff = dff[dff["Vehicle ID"].isin(vehicle_val)]

    return dff.to_dict("records"), create_figure(dff)

# Serve video files
@server.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory(STATIC_DIR, path)

# Run the App
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7060)
