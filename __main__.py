from dash import Dash, html, dcc
import plotly.express as px
import requests
import pandas as pd
from flask import Flask, request, render_template
import plotly.graph_objects as go
import logging

# Настройка логирования в начале файла, после импортов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Инициализация Flask и Dash
server = Flask(__name__)
app = Dash(__name__, server=server)

API_KEY = "7ddc2f019ed6ac507bbf5075056a6183"

def get_weather_by_city(city, days=1):
    try:
        logging.info(f"Получение погоды для города: {city}")
        params = {"q": city, "appid": API_KEY, "units": "metric"}
        response = requests.get("http://api.openweathermap.org/data/2.5/weather", params=params)
        response.raise_for_status()
        data = response.json()
        
        lat = data['coord']['lat']
        lon = data['coord']['lon']
        logging.info(f"Получены координаты для {city}: lat={lat}, lon={lon}")
        
        forecast_url = "http://api.openweathermap.org/data/2.5/forecast"
        forecast_params = {
            "lat": lat,
            "lon": lon,
            "appid": API_KEY,
            "units": "metric",
            "cnt": days * 8
        }
        
        forecast_response = requests.get(forecast_url, forecast_params)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()
        logging.info(f"Успешно получен прогноз для {city}")
        
        return [{
            "city": city,
            "date": item['dt_txt'],
            "temperature": item['main']['temp'],
            "wind_speed": item['wind']['speed'],
            "rain_probability": item.get('pop', 0) * 100
        } for item in forecast_data['list']]
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка сети для города {city}: {str(e)}")
        return []
    except KeyError as e:
        logging.error(f"Ошибка в структуре данных для города {city}: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"Неожиданная ошибка для города {city}: {str(e)}")
        return []


@server.route('/check_weather', methods=['POST'])
def check_weather():
    try:
        start_city = request.form.get('start')
        end_city = request.form.get('end')
        forecast_days = int(request.form.get('forecast_days', 1))
        
        cities = f"{start_city},{end_city}"
        return f'<script>window.location.href = "/dashboard/?cities={cities}&days={forecast_days}";</script>'
    except Exception as e:
        return render_template('error.html', message=str(e))

# Dash приложение
app.layout = html.Div([
    html.H1('Прогноз погоды для маршрута'),
    
    html.Div([
        html.Label('Города: '),
        dcc.Input(id='cities-input', type='text', placeholder='Москва,Санкт-Петербург'),
        
        html.Label(' Дни: '),
        dcc.Dropdown(
            id='days-dropdown',
            options=[
                {'label': '1 день', 'value': 1},
                {'label': '2 дня', 'value': 2},
                {'label': '3 дня', 'value': 3},
                {'label': '4 дня', 'value': 4}
            ],
            value=1,
            style={'width': '200px', 'display': 'inline-block'}
        ),
        
        html.Button('Обновить', id='update-button', n_clicks=0),
    ], style={'margin': '20px'}),
    
    dcc.Graph(id='route-map'),
    
    dcc.Graph(id='temperature-graph'),
    dcc.Graph(id='wind-graph'),
    dcc.Graph(id='rain-graph'),
    
    html.A('На главную', href='/')
])

from dash.dependencies import Input, Output, State

@app.callback(
    [Output('temperature-graph', 'figure'),
     Output('wind-graph', 'figure'),
     Output('rain-graph', 'figure'),
     Output('route-map', 'figure')],
    [Input('update-button', 'n_clicks')],
    [State('cities-input', 'value'),
     State('days-dropdown', 'value')]
)
def update_graphs(n_clicks, cities_string, days):
    if not cities_string or n_clicks == 0:
        return {}, {}, {}, {}
    
    cities = [city.strip() for city in cities_string.split(',')]
    all_data = []
    coordinates = []
    
    for city in cities:
        forecast = get_weather_by_city(city, days=days)
        all_data.extend(forecast)
        
        params = {"q": city, "appid": API_KEY, "units": "metric"}
        response = requests.get("http://api.openweathermap.org/data/2.5/weather", params=params)
        data = response.json()
        coordinates.append({
            'city': city,
            'lat': data['coord']['lat'],
            'lon': data['coord']['lon'],
            'temp': data['main']['temp']
        })
    
    df = pd.DataFrame(all_data)
    if df.empty:
        return {}, {}, {}, {}
    
    temp_fig = px.line(df, x='date', y='temperature', color='city',
                       title=f'Температура (°C) - Прогноз на {days} дней')
    temp_fig.update_layout(
        xaxis_title="Дата и время",
        yaxis_title="Температура (°C)"
    )
    
    wind_fig = px.line(df, x='date', y='wind_speed', color='city',
                       title=f'Скорость ветра (м/с) - Прогноз на {days} дней')
    wind_fig.update_layout(
        xaxis_title="Дата и время",
        yaxis_title="Скорость ветра (м/с)"
    )
    
    rain_fig = px.line(df, x='date', y='rain_probability', color='city',
                       title=f'Вероятность осадков (%) - Прогноз на {days} дней')
    rain_fig.update_layout(
        xaxis_title="Дата и время",
        yaxis_title="Вероятность осадков (%)"
    )
    
    map_fig = go.Figure()
    
    map_fig.add_trace(go.Scattermapbox(
        mode='lines+markers',
        lon=[coord['lon'] for coord in coordinates],
        lat=[coord['lat'] for coord in coordinates],
        marker={'size': 10},
        line={'width': 2},
        name='Маршрут'
    ))
    
    for coord in coordinates:
        map_fig.add_trace(go.Scattermapbox(
            mode='markers+text',
            lon=[coord['lon']],
            lat=[coord['lat']],
            marker={
                'size': 15,
                'color': 'red',
                'symbol': 'circle'
            },
            text=f"{coord['city']}: {coord['temp']}°C",
            textposition="top center",
            name=coord['city']
        ))
    
    map_fig.update_layout(
        mapbox={
            'style': "carto-darkmatter"  ,
            'center': {'lon': coordinates[0]['lon'], 
                      'lat': coordinates[0]['lat']},
            'zoom': 5
        },
        margin={'l': 0, 'r': 0, 'b': 0, 't': 30},
        height=600,
        title='Маршрут и текущая температура'
    )
    
    return temp_fig, wind_fig, rain_fig, map_fig

if __name__ == '__main__':
    app.run_server(debug=0, port=5000)