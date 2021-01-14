import flask
import dash
import dash_html_components as html
import dash_core_components as dcc
import dash_table
from dash.dependencies import Input, Output
import requests
import pandas as pd
import numpy as np
from newsapi import NewsApiClient
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dropdown import countries, countries_options
import math
import copy

pd.set_option('display.max_columns', None)
app = dash.Dash(__name__, meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}])
server = app.server
app.config.suppress_callback_exceptions = True
app.title = 'COVID-19 Analytics'

alpha_2_url = 'https://pkgstore.datahub.io/core/country-list/data_json/data/8c458f2d15d9f2119654b29ede6e45b8/data_json.json'
alpha_2_response = requests.request("GET", alpha_2_url, headers={}, data = {}).json()

alpha_3_url = 'https://raw.githubusercontent.com/lukes/ISO-3166-Countries-with-Regional-Codes/master/slim-3/slim-3.json'
alpha_3_response = requests.request("GET", alpha_3_url, headers={}, data = {}).json()

def get_alpha_code_2_digit(country):
    if country == None:
        return 'CA'
    elif country == 'Korea (South)':
        return 'KR'
    elif country == 'Iran':
        return 'IR'
    elif country == 'United Kingdom':
        return 'GB'
    elif country == 'Russia':
        return 'RU'
    elif country == 'Venezuela':
        return 'VN'
    elif country == 'Moldova':
        return 'MD'

    for i in alpha_2_response:
        if country.lower() == i['Name'].lower():
            return (i['Code'])
    return 'US'


def get_alpha_code_3_digit(country):
    if country == None:
        return 'CAN'
    elif country == 'Korea (South)':
        return 'KOR'
    elif country == 'Iran':
        return 'IRN'
    elif country == 'United Kingdom':
        return 'GBR'
    elif country == 'Russia':
        return 'RUS'
    elif country == 'Venezuela':
        return 'VEN'
    elif country == 'Moldova':
        return 'MDA'

    for i in alpha_3_response:
        if country.lower() == i['name'].lower():
            return (i['alpha-3'])
    return 'USA'

def overlap(annotations):
    moveUp = [20, 40, 80, 130, 190, 260, 340, 430, 530, 640]
    counter = 0
    moveUpCounter = 0
    for count, i in enumerate(annotations):
        ann = copy.copy(annotations)
        del ann[counter]
        for j in ann:
            if i['y'] - 10 <= j['y'] <= i['y'] + 10:
                print(i['y'], ' : ', j['y'])
                print(i['text'], ' : ', j['text'])
                annotations[count]['ay'] -= moveUp[moveUpCounter]
                moveUpCounter += 1
                break
        counter += 1

    if annotations[3]['text'] in ['Canada', 'Italy', 'Australia']:
        del annotations[3]

    return annotations

def getSummaryDataProvince():
    url = "https://corona.lmao.ninja/v2/jhucsse"
    try:
        response = requests.request("GET", url, headers={}, data = {}).json()
    except:
        print('\nAPI ERROR: Could Not Get JSON Data\n')

    data = []
    for location in response:
        data.append([location['country'], location['province'], location['stats']['confirmed'], location['stats']['recovered'], location['stats']['deaths'], location['coordinates']['latitude'], location['coordinates']['longitude'], get_alpha_code_2_digit(location['country'])])

    df_summary = pd.DataFrame(data, columns=['Country', 'Province', 'Total Confirmed Cases', 'Total Recovered', 'Total Deaths', 'latitude', 'longitude', 'Code'])
    df_summary = df_summary.drop(df_summary[df_summary['latitude'] == ''].index)
    df_summary[['Total Confirmed Cases', 'Total Recovered', 'Total Deaths', 'latitude', 'longitude']] = df_summary[['Total Confirmed Cases', 'Total Recovered', 'Total Deaths', 'latitude', 'longitude']].apply(pd.to_numeric, errors='coerce')
    df_summary['Province'].fillna(df_summary['Country'], inplace=True)
    df_summary['Country'].loc[(df_summary['Country'] == 'US')] = 'United States of America'
    return df_summary

def getSummaryData():
    url = "https://api.covid19api.com/summary"
    try:
        response = requests.request("GET", url, headers={}, data = {}).json()
    except:
        print('\nAPI ERROR: Could Not Get JSON Data\n')

    overall_data = response['Global']
    country_data = response['Countries']

    vis_geo_data = []

    for country in country_data:
        vis_geo_data.append([country['Country'], country['TotalConfirmed'], country['NewConfirmed'], country['TotalDeaths'], country['NewDeaths'], country['TotalRecovered'], get_alpha_code_2_digit(country['Country'])])
    
    lat_long = pd.read_csv('countries.csv')

    vis_geo_data_frame = pd.DataFrame(vis_geo_data, columns=["Country", "Total Confirmed Cases", "New Confirmed Cases", "Total Deaths", "New Deaths", "Total Recovered", "Code"])
    vis_geo_data_frame = pd.merge(left=vis_geo_data_frame, right=lat_long, how='left', left_on='Code', right_on='country')
    vis_geo_data_frame.drop(['country', 'name'], axis=1, inplace=True)
    
    return vis_geo_data_frame, overall_data

def get_slug_data():
    import requests
    url = "https://api.covid19api.com/countries"
    return requests.request("GET", url, headers={}, data = {}).json()

def get_slug(data, location):
    print("HIL ",location)
    try:
        val = countries[location].lower()
    except:
        val = location.replace('-', ' ')
        

    print("XXX111: ", val)
    if location == 'Russia':
        return 'russia'
    elif location == 'Iran':
        return 'Iran, Islamic Republic of'
    
    for country in data:
        if country['Country'].lower() == val:
            return country['Slug']
    
    return 'US'

def getNewsTable(hoverData, value):
    try:
        location = (hoverData['points'][0])['hovertext']
        location = summary_data_province.loc[summary_data_province['Province'] == location, 'Country'].values[0]
    except:
        location = value

    newsapi = NewsApiClient(api_key='fc196ae87d3749cc856e46cce3e6d869')

    try:
        top_headlines = newsapi.get_top_headlines(q='Coronavirus',
                                            language='en',
                                            country=get_alpha_code_2_digit(location).lower())
    except:
        print('Error Getting News Articles')
        top_headlines = newsapi.get_top_headlines(q='Coronavirus',
                                            language='en',
                                            country='us')

    html_news = []
    for count, article in enumerate(top_headlines['articles']):
        if count == 3:
            break
        html_news.append(html.Table([
            html.Tbody([
                html.Tr([
                    html.Td([
                        html.Div([
                            html.P([
                                article['source']['name']], style={'font-size': '12px', 'color': '#9e9e9e'}),
                            html.A(
                                html.H6([article['title']], style={'font-size': '14px', 'font-weight': 'bold'}), href="{}".format(article['url']), target="_blank",
                            ),   
                            html.P([article['publishedAt'][:10]], style={'font-size': '12px', 'color': '#9e9e9e'})
                        ])], style={'width': '65%', 'padding-left': '10px'}),
                    html.Td([
                        html.Img(src="{}".format(article['urlToImage']), style={"height": "100px", "width": "140px", "border-radius": "10%"})
                    ], style={'width': '25%', 'padding-right': '10px'}),
                ])
            ])     
        ]))

    return html_news

def get_testing_and_per_million_data():
    df = pd.read_csv('https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv')
    df = df[['iso_code', 'location', 'date', 'total_cases_per_million', 'total_deaths_per_million', 'total_tests_per_thousand', 'new_cases', 'new_deaths', 'new_cases_per_million', 'new_deaths_per_million', 'total_cases', 'new_tests_per_thousand', 'new_tests', 'total_tests']]
    
    #df['new_tests_per_thousand'].fillna(method='ffill', inplace=True)
    return df

summary_data, overall_data = getSummaryData()
summary_data.sort_values(['Total Confirmed Cases'], ascending=False, inplace=True)

slug_data = get_slug_data()
summary_data_province = getSummaryDataProvince()

owid_data = get_testing_and_per_million_data()

def create_confirmed_cases_data_table():
    data_table = dash_table.DataTable(
        id='confirmed-cases-data-table',
        data=summary_data[["Country", "Total Confirmed Cases", "Total Deaths"]].to_dict('records'),
        columns=[{'id': c, 'name': c} for c in summary_data[["Country", "Total Confirmed Cases", "Total Deaths"]].columns],
        fixed_rows={'headers': True},
        style_table={'height': '490px', 
                    'overflowY': 'auto'},
        style_cell={'maxWidth': '40px', 
                    'text-align': 'center', 
                    'padding': '10px', 
                    'font-size': '15px', 
                    'font-family': 'Helvetica', 
                    'color': '#f9f9f9', 
                    'backgroundColor': '#1f1f1f', 
                    'border': '#888'},
        style_header={
            'color': '#f9f9f9', 
            'backgroundColor': '#000000',
            'font-weight': '600',
            'font-size': '16px',
            'font-family': 'Montserrat, sans-serif',
            'border': '#888'}
    )
    return data_table

def create_map_fig(summary_data, lat_input=25, long_input=0, zoom_input=0.7, marker_size_input=25):
    fig = px.scatter_mapbox(summary_data_province, 
                        lat="latitude", 
                        lon="longitude", 
                        size="Total Confirmed Cases",
                        color_continuous_scale="Viridis", 
                        size_max=25, 
                        hover_name='Province',
                        hover_data=["Total Confirmed Cases", "Total Deaths", "Total Recovered"])

    fig.update_layout(coloraxis_showscale=False, 
                      margin={'r': 20, 'l': 20, 't': 70, 'b': 35}, 
                      title='Confirmed Cases by Country (Click to see Country Specific Data)', 
                      height=502,
                      mapbox=dict(
                          accesstoken='pk.eyJ1Ijoicm9oYW5yYXYiLCJhIjoiY2thYW15eGRpMHBrazJycGphYnBvZmh3MSJ9.fc1JTRkhh2Vn3Q9k2QwbTw',
                          zoom=zoom_input,
                          center=go.layout.mapbox.Center(lat=lat_input, lon=long_input),
                          style='dark'),
                      template='plotly_dark')
    return fig
    

def get_day_one_data(hoverData, value):
    try:
        location = (hoverData['points'][0])['hovertext']
    except:
        location = value.encode('utf-8')
    
    print('\n\n LOCATION: ',location, '\n\n')
    
    try:
        country_val = summary_data_province.loc[summary_data_province['Province'] == location, 'Country'].values[0]
        print('Country VALUE: ', country_val)
        slug = get_slug(slug_data, country_val)
    except:
        slug = get_slug(slug_data, location)
        country_val = None

    url = "https://api.covid19api.com/total/dayone/country/{}".format(slug)
    print('URL: ', url)

    response = requests.request("GET", url, headers={}, data = {}).json()

    data = []
    for day in response:
        data.append([day['Date'], day['Confirmed'], day['Deaths']])
    
    data_df = pd.DataFrame(data, columns=['date', 'cases', 'deaths'])
    data_df['date'] = data_df['date'].str.slice(stop=10) 
    data_df['date'] = pd.to_datetime(data_df['date'], format='%Y-%m-%d')
    return data_df, location.decode('utf-8').replace('-', ' ').capitalize(), country_val

def get_global_data():
    url = 'https://corona-api.com/timeline'

    response = requests.request("GET", url, headers={}, data = {}).json()
    data_cumulative = []
    data_daily = []

    for day in response['data']:
        data_cumulative.append([day['confirmed'], day['deaths'], day['date'], day['recovered']])
        data_daily.append([day['new_confirmed'], day['new_deaths'], day['new_recovered'], day['date']])

    cum_data = pd.DataFrame(data_cumulative, columns=['confirmed', 'deaths', 'date', 'recovered'])
    cum_data['date'] = pd.to_datetime(cum_data['date'], format='%Y-%m-%d')
    day_data = pd.DataFrame(data_daily, columns=['new_confirmed', 'new_deaths', 'new_recovered', 'date'])
    day_data['date'] = pd.to_datetime(day_data['date'], format='%Y-%m-%d')

    return cum_data, day_data

cumulative_data, daily_data = get_global_data()
daily_data = daily_data.iloc[1:]
cumulative_data = cumulative_data.iloc[1:]

def create_confirmed_cases_graph(log_scale):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cumulative_data['date'], y=cumulative_data['confirmed'],
                        mode='lines+markers',
                        name='Confirmed Cases'))
    fig.add_trace(go.Scatter(x=cumulative_data['date'], y=cumulative_data['deaths'],
                        mode='lines+markers',
                        name='Deaths'))
    fig.add_trace(go.Scatter(x=cumulative_data['date'], y=cumulative_data['recovered'],
                        mode='lines+markers',
                        name='Recovered'))
    fig.update_layout(margin={'r': 25, 'l': 10, 'b': 0}, height=490, xaxis_title='', yaxis_title='', title='Global Cumulative Confirmed Cases', legend=dict(x=0, y=1, traceorder="normal"), template="plotly_dark", hovermode='x')

    if log_scale:
        fig.update_layout(yaxis_type="log")

    return fig

def create_daily_cases_graph():
    t1 = go.Bar(x=daily_data['date'], y=daily_data['new_confirmed'], name='Confirmed Cases')
    t2 = go.Bar(x=daily_data['date'], y=daily_data['new_deaths'], name='Deaths')
    data = [t1, t2]
    fig = go.Figure(data=data)
    fig.update_layout(margin={'r': 25, 'l': 10, 'b': 0}, height=490, xaxis_title='', yaxis_title='', title='Global Daily Confirmed Cases', barmode='overlay', legend=dict(x=0, y=1, traceorder="normal"), template="plotly_dark")
    
    return fig

def update_country_cases(location, value):
    if location == None:
        location = 'Canada'

    df, location_new, country_val = get_day_one_data(hoverData=location, value=value)

    if country_val != None:
        location = country_val
    
    t1 = go.Scatter(x = df['date'], y = df['cases'], name = 'Cases', mode='lines+markers')
    t2 = go.Scatter(x = df['date'], y = df['deaths'], name = 'Deaths', mode='lines+markers')
    fig = go.Figure(data=[t1,t2])
    fig.update_layout(margin={'r': 10, 't': 80, 'b': 0, 'l': 15}, xaxis_title='', yaxis_title='', legend=dict(x=0, y=1, traceorder="normal"), title='Confirmed Cases: {}'.format(location.title()), template="plotly_dark", hovermode='x')

    return fig

def get_pie_graph():
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Daily Cases", "Daily Deaths"), specs=[[{"type": "pie"}, {"type": "pie"}]])
    data = (summary_data[['Country', 'New Confirmed Cases', 'New Deaths']])
    fig.add_trace(go.Pie(labels=data['Country'], values=data['New Confirmed Cases']), row=1, col=1)
    fig.add_trace(go.Pie(labels=summary_data['Country'], values=summary_data['New Deaths']), row=1, col=2)
    fig.update_layout(margin={'r': 10, 'l': 10, 'b': 30}, showlegend=False, title='Confirmed Cases/Deaths by Region', template="plotly_dark", yaxis_type='log', height=490)
    fig.update_traces(textposition='inside', textinfo='percent+label')

    return fig

def get_testing_graph(hoverData, value, data=owid_data):
    try:
        location = (hoverData['points'][0])['hovertext']
        location = summary_data_province.loc[summary_data_province['Province'] == location, 'Country'].values[0]
    except:
        location = value

    data_italy = data[data['iso_code'] == 'ITA'].iloc[51:]
    data_canada = data[data['iso_code'] == 'CAN'].iloc[51:]
    data_aus = data[data['iso_code'] == 'AUS'].iloc[51:]
    print(get_alpha_code_3_digit(location))
    data = data[data['iso_code'] == get_alpha_code_3_digit(location)].iloc[51:]


    trace3 = go.Scatter(x = data_italy['date'], y = data_italy['new_tests_per_thousand'],  name = 'Italy', mode='lines', line=dict(color='green', shape='spline', smoothing=1.3))
    trace5 = go.Scatter(x = data_canada['date'], y = data_canada['new_tests_per_thousand'],  name = 'Canada', mode='lines', line=dict(color='red', shape='spline', smoothing=1.3))
    trace6 = go.Scatter(x = data_aus['date'], y = data_aus['new_tests_per_thousand'],  name = 'Australia', mode='lines', line=dict(color='purple', shape='spline', smoothing=1.3))
    trace1 = go.Scatter(x = data['date'], y = data['new_tests_per_thousand'], name = '{}'.format(location.title()), mode='lines', line=dict(color='royalblue', shape='spline', smoothing=1.3))

    data = [trace3, trace6, trace5, trace1]
    annotation = []

    for trace in data:
        counter = 1
        for i in range(len(trace.y)):
            if np.isnan(trace.y[len(trace.y)-counter]):
                counter += 1
                continue
            break
    
        print(counter, ' : ', trace.name)
        x = trace.x[len(trace.x)-counter]
        y = trace.y[len(trace.y)-counter]
    
        annotation.append(dict(
            x=x,
            y=y,
            xref="x",
            yref="y",
            text=trace.name,
            showarrow=True,
            arrowhead=3,
            ax=50,
            ay=0
            ))

    fig = go.Figure(data = data)
    fig.update_layout(annotations = annotation, xaxis_title='', yaxis_title='', yaxis_type='linear',  margin={'r': 15, 't': 80, 'b': 0, 'l': 25}, title='Daily New Tests Conducted per Thousand for {}'.format(location.title()), template="plotly_dark", legend_orientation="h", hovermode='x')

    return fig

def per_million_data(hoverData, value, data=owid_data):
    try:
        location = (hoverData['points'][0])['hovertext']
        location = summary_data_province.loc[summary_data_province['Province'] == location, 'Country'].values[0]
    except:
        location = value
    
    data_italy = data[data['iso_code'] == 'ITA'].iloc[52:]
    data_canada = data[data['iso_code'] == 'CAN'].iloc[52:]
    data_aus = data[data['iso_code'] == 'AUS'].iloc[52:]
    data = data[data['iso_code'] == get_alpha_code_3_digit(location)].iloc[52:]

    trace3 = go.Scatter(x = data_italy['date'], y = data_italy['new_cases_per_million'],  name = 'Italy', mode='lines', line=dict(color='green', shape='spline', smoothing=1.3))
    trace5 = go.Scatter(x = data_canada['date'], y = data_canada['new_cases_per_million'],  name = 'Canada', mode='lines', line=dict(color='red', shape='spline', smoothing=1.3))
    trace6 = go.Scatter(x = data_aus['date'], y = data_aus['new_cases_per_million'],  name = 'Australia', mode='lines', line=dict(color='purple', shape='spline', smoothing=1.3))
    trace1 = go.Scatter(x = data['date'], y = data['new_cases_per_million'], name = '{}'.format(location.title()), mode='lines', line=dict(color='royalblue', shape='spline', smoothing=1.3))
    
    data = [trace3, trace5, trace6, trace1]
    annotation = []

    for trace in data:
        counter = 1
        for i in range(len(trace.y)):
            if np.isnan(trace.y[len(trace.y)-counter]):
                counter += 1
                continue
            break
    
        print(counter, ' : ', trace.name)
        x = trace.x[len(trace.x)-counter]
        y = trace.y[len(trace.y)-counter]
    
        annotation.append(dict(
            x=x,
            y=y,
            xref="x",
            yref="y",
            text=trace.name,
            showarrow=True,
            arrowhead=3,
            ax=50,
            ay=0,
            ))
    annotations = overlap(annotation)
    fig = go.Figure(data = data)
    fig.update_layout(annotations = annotations, title="New Cases per Million of {}".format(location.title()), xaxis_title="", yaxis_title='', margin={'r': 15, 't': 80, 'b': 0, 'l': 25}, legend_orientation="h", template="plotly_dark", hovermode='x')

    return fig

def cases_fatalities_ratio(hoverData, value, data=owid_data):
    try:
        location = (hoverData['points'][0])['hovertext']
        location = summary_data_province.loc[summary_data_province['Province'] == location, 'Country'].values[0]
    except:
        location = value

    data[['total_tests', 'total_cases']].fillna(method='ffill', inplace=True)
    data['Tests per Case'] = data['total_tests'] / data['total_cases']
    
    data_italy = data[data['iso_code'] == 'ITA']
    data_canada = data[data['iso_code'] == 'CAN']
    data_aus = data[data['iso_code'] == 'AUS']
    data = data[data['iso_code'] == get_alpha_code_3_digit(location)]

    data_italy = data_italy.loc[data_italy['Tests per Case'] <= 1000]
    data_canada = data_canada.loc[data_canada['Tests per Case'] <= 1000]
    data_aus = data_aus.loc[data_aus['Tests per Case'] <= 1000]
    data = data.loc[data['Tests per Case'] <= 1000]

    trace3 = go.Scatter(x = data_italy['date'], y = data_italy['Tests per Case'],  name = 'Italy', mode='lines', line=dict(color='green', shape='spline', smoothing=1.3))
    trace5 = go.Scatter(x = data_canada['date'], y = data_canada['Tests per Case'],  name = 'Canada', mode='lines', line=dict(color='red', shape='spline', smoothing=1.3))
    trace6 = go.Scatter(x = data_aus['date'], y = data_aus['Tests per Case'],  name = 'Australia', mode='lines', line=dict(color='purple', shape='spline', smoothing=1.3))
    trace1 = go.Scatter(x = data['date'], y = data['Tests per Case'], name = '{}'.format(location.title()), mode='lines', connectgaps=True, line=dict(color='royalblue', shape='spline', smoothing=1.3))
    
    data = [trace3, trace5, trace6, trace1]
    
    annotation = []

    for trace in data:
        if len(trace.x) == 0:
            continue

        counter = 1
        for i in range(len(trace.y)):
            if np.isnan(trace.y[len(trace.y)-counter]):
                counter += 1
                continue
            break
    
        print(counter, ' : ', trace.name)
        x = trace.x[len(trace.x)-counter]
        y = trace.y[len(trace.y)-counter]
    
        annotation.append(dict(
            x=x,
            y=math.log10(y),
            xref="x",
            yref="y",
            text=trace.name,
            showarrow=True,
            arrowhead=3,
            ax=50,
            ay=0
            ))

    fig = go.Figure(data = data)
    fig.update_layout(annotations = annotation, title="Tests Conducted per Confirmed Case for {}".format(location.title()), xaxis_title="", yaxis_title='', margin={'r': 15, 't': 80, 'b': 0, 'l': 25}, legend_orientation="h", template="plotly_dark", yaxis_type='log', hovermode='x')

    return fig

def daily_country_data(hoverData, value):
    try:
        location = (hoverData['points'][0])['hovertext']
        location = summary_data_province.loc[summary_data_province['Province'] == location, 'Country'].values[0]
    except:
        location = value

    df = owid_data
    df = df[df['iso_code'] == get_alpha_code_3_digit(location)]
    trace1 = go.Scatter(x = df['date'], y = df['new_cases'], name = 'Daily Cases')
    trace2 = go.Scatter(x = df['date'], y = df['new_deaths'],  name = 'Daily Deaths')
    fig = go.Figure(data = [trace1, trace2])
    fig.update_layout(title="Daily Cases/Deaths for {}".format(location.title()), xaxis_title="", yaxis_title='', barmode='overlay', legend=dict(x=0, y=1, traceorder="normal"), template="plotly_dark", margin={'r': 10, 't': 80, 'b': 0, 'l': 15}, hovermode='x')

    return fig

def top_countries_graph(data=summary_data):
    data = data.head(20)
    trace1 = go.Bar(x = data['Country'], y = data['Total Confirmed Cases'], name = 'Confirmed Cases')
    trace2 = go.Bar(x = data['Country'], y = data['Total Deaths'],  name = 'Deaths')
    fig = go.Figure(data = [trace1, trace2])
    fig.update_layout(barmode='overlay', title='Countries with highest confirmed cases', yaxis_title="", showlegend=False, height=490, template="plotly_dark", margin={'r': 25, 'l': 5}, hovermode='x')

    return dcc.Graph(figure=fig)

def country_pie_dist(hoverData, value):
    try:
        location = (hoverData['points'][0])['hovertext']
        location = summary_data_province.loc[summary_data_province['Province'] == location, 'Country'].values[0]
    except:
        location = value
    
    df = summary_data_province[summary_data_province['Country'] == location]

    fig = make_subplots(rows=1, cols=2, subplot_titles=("Total Cases", "Total Deaths"), specs=[[{"type": "pie"}, {"type": "pie"}]])
    data = (df[['Province', 'Total Confirmed Cases', 'Total Deaths']])
    fig.add_trace(go.Pie(labels=data['Province'], values=data['Total Confirmed Cases']), row=1, col=1)
    fig.add_trace(go.Pie(labels=data['Province'], values=data['Total Deaths']), row=1, col=2)
    fig.update_layout(margin={'r': 10, 'l': 10, 'b': 30}, showlegend=False, title='Confirmed Cases/Deaths by Region for {}'.format(location.title()), template="plotly_dark")
    fig.update_traces(textposition='inside', textinfo='percent+label')

    return fig


# APP LAYOUT
app.layout = html.Div([
    html.Div([
        html.H1('COVID-19 Analytics Dashboard',
                style = {'font-size': '40px',
                        'font-weight': '900'}),
        html.P("Click on the areas in the map to see country specific testing, cases, and fatalities data. Use the menu to zoom onto a specfic area.", 
                style = {'font-size': '16px',
                        'margin-top': '-12.5px'}),
         html.A(html.P("Created by Rohan Ravindran.", 
                style = {'font-size': '13px'}), href='https://www.linkedin.com/in/rohan-r-74506712b/', target="_blank", style={'font-weight': '300'}),
            ], 
            style = {'text-align': 'center',
                    'font-family': "Montserrat, sans-serif",
                    'color': '#f9f9f9',
                    'margin-top': '50px'}
            ),
    #NEW SECTION
    html.Div([
        html.Div([
            html.Div([
                html.P(
                    "Zoom to a specific area:",
                    className='control_label'
                    ),

                dcc.Dropdown(
                    id="countries-dropdown",
                    options=countries_options,
                    value='0',
                    className='dcc_control'
                ),
            ])
        ], className='four columns pretty_container_modified'),

        html.Div([
            html.Div([
                html.Div(
                    [html.H6('{:,}'.format(overall_data['TotalConfirmed']), style={'font-weight': '900', 'color': '#f9f9f9', 'font-size': '275%'}), 
                    html.P("Total Confirmed Cases", style={'color': '#f9f9f9'})],
                    style={'flex': '1'},
                    className="mini_container",
                    id='total-confirmed'
                ),
                html.Div(
                    [html.H6('{:,}'.format(overall_data['TotalDeaths']), style={'font-weight': '900', 'color': '#e60600', 'font-size': '275%'}), 
                    html.P("Total Deaths", style={'color': '#f9f9f9'})],
                    style={'flex': '1'},
                    className="mini_container",
                    id='total-deaths'
                ),
                html.Div(
                    [html.H6('{:,}'.format(overall_data['TotalRecovered']), style={'font-weight': '900', 'color': '#70a901', 'font-size': '275%'}), 
                    html.P("Total Recovered", style={'color': '#f9f9f9'})],
                    style={'flex': '1'},
                    className="mini_container",
                    id='total-recovered'
                )
            ], id='info-container',
            className='row container-display')
        ], 
        id='right-column',
        className='eight columns')

    ],
    className='row flex-display margin-setter'),

    # SECTION 1
    html.Div([
        html.Div([
            dcc.Graph(id="map_graph", figure=create_map_fig(summary_data))
        ], 
        className='pretty_container seven columns'),

        html.Div([
            dcc.Graph(id='curve_graph', figure=update_country_cases(location=None, value='Canada'), style={'margin-bottom': '15px'}),
            html.Div([
                html.Button('Cases/Deaths', id='cases-deaths', n_clicks = 0, className='btn-margin-mod-49'),
                html.Button('Daily Cases/Deaths', id='daily-cases-deaths', n_clicks = 0, className='btn-margin-mod-49'),
            ], style={'text-align': 'center', 'margin-top': '15px'}, className='btn-display')
        ],
        className='pretty_container five columns')
    ], 
    className='row flex-display'),

     # SECTION 2
    html.Div([
        html.Div([
            dcc.Graph(id='dist_graphs', figure=get_testing_graph(hoverData=None, value='Canada'), style={'margin-bottom': '15px'}),
            html.Div([ 
                html.Button('Testing Data', id='test', n_clicks = 0, className='btn-margin-mod-24'),
                html.Button('Tests per case', id='cases-fatalities-ratio', n_clicks = 0, className='btn-margin-mod-24'),
                html.Button('Per million', id='per-milli-cases-death', n_clicks = 0, className='btn-margin-mod-24'),
                html.Button('Distribution', id='country-distribution', n_clicks = 0, className='btn-margin-mod-24'),
            ], style={'text-align': 'center', 'margin-top': '15px'}, className='btn-display')
        ], className='pretty_container seven columns'),
        html.Div([
            html.Table([
                html.Thead([
                     html.Tr([
                        html.Th([
                            html.Div("Top News")
                        ], colSpan="2", style={'font-size': '20px', 'color': '#f2f2f2'})
                    ])
                ]),
                html.Div(getNewsTable(hoverData=None, value='Canada'), id='news-table')
            ])
        ], className='pretty_container five columns')
        
    ], className='row flex-display'),

    html.Div([
        html.H1('Global Information',
                style = {'font-size': '30px',
                        'font-weight': '900',
                        'margin-top': '22px'}),
        html.P("The following graphs contain global information about the COVID-19 pandemic.", 
                style = {'font-size': '16px',
                        'margin-top': '-12.5px',
                        'margin-bottom': '12.5px'}),
                ], style = {'font-family': "Montserrat, sans-serif",
                            'color': '#f9f9f9',
                            'display': 'inline',
                            'text-align': 'center'},
        className='row flex-display margin-setter align'),

    # SECTION 3
    html.Div([
        html.Div([
            html.Div([
                dcc.Graph(id='cases_graph', figure=(get_pie_graph()), style={'margin-bottom': '15px'})
            ]),
            html.Div([ 
		html.Button('Distribution', id='cases-dist', n_clicks = 0, className='btn-margin-mod-24'),
                html.Button('Daily Cases', id='day-conf', n_clicks = 0, className='btn-margin-mod-24'),
                html.Button('Cumulative', id='cum-conf', n_clicks = 0, className='btn-margin-mod-24'),
                html.Button('Logarithmic', id='log-cum-conf', n_clicks = 0, className='btn-margin-mod-24'),
            ], style={'text-align': 'center', 'margin-top': '15px'}, className='btn-display')
        ],
        className='pretty_container seven columns'),
        html.Div([
            html.Div(top_countries_graph(), id='graph-top', style={'margin-bottom': '15px'}),
            html.Div([
                html.Button('Top Countries', id='top-countries-bar-chart', n_clicks = 0, className='btn-margin-mod-49'),
                html.Button('Deaths/Cases Table', id='table-cases-death', n_clicks = 0, className='btn-margin-mod-49'),
            ], style={'text-align': 'center', 'margin-top': '15px'}, className='btn-display')
        ],
        className='pretty_container five columns')
    ], 
    className='row flex-display'),

])

@app.callback(
    Output('countries-dropdown', 'value'),
    [Input('map_graph', 'clickData')])
def update_confirmed_cases(clickData):
    try:
        country = (clickData['points'][0])['hovertext']
    except:
        country = 'Global'
    
    for i in range(len(countries)):
        if countries[str(i)].lower() == country.lower():
            return str(i)

    return '0'

@app.callback(
    Output('total-confirmed', 'children'),
    [Input('map_graph', 'clickData')])
def update_confirmed_cases(clickData):
    try:
        country = (clickData['points'][0])['hovertext']
    except:
        return [html.H6('{:,}'.format(overall_data['TotalConfirmed']), style={'font-weight': '900', 'color': '#f9f9f9', 'font-size': '275%'}), html.P("Total Confirmed Cases", style={'color': '#f9f9f9'})]
        
    data = summary_data_province[summary_data_province["Province"] == country]
    return [html.H6('{:,}'.format(data['Total Confirmed Cases'].values[0]), style={'font-weight': '900', 'color': '#f9f9f9', 'font-size': '275%'}), html.P("Total Confirmed Cases", style={'color': '#f9f9f9'})]
 
@app.callback(
    Output('total-deaths', 'children'),
    [Input('map_graph', 'clickData')])
def update_confirmed_cases(clickData):
    try:
        country = (clickData['points'][0])['hovertext']
    except:
        return [html.H6('{:,}'.format(overall_data['TotalDeaths']), style={'font-weight': '900', 'color': '#e60600', 'font-size': '275%'}), html.P("Total Deaths", style={'color': '#f9f9f9'})]
        
    data = summary_data_province[summary_data_province["Province"] == country]
    return [html.H6('{:,}'.format(data['Total Deaths'].values[0]), style={'font-weight': '900', 'color': '#e60600', 'font-size': '275%'}), html.P("Total Deaths", style={'color': '#f9f9f9'})]

@app.callback(
    Output('total-recovered', 'children'),
    [Input('map_graph', 'clickData')])
def update_confirmed_cases(clickData):
    try:
        country = (clickData['points'][0])['hovertext']
    except:
        return [html.H6('{:,}'.format(overall_data['TotalRecovered']), style={'font-weight': '900', 'color': '#70a901', 'font-size': '275%'}), html.P("Total Recovered", style={'color': '#f9f9f9'})]
        
    data = summary_data_province[summary_data_province["Province"] == country]
    return [html.H6('{:,}'.format(data['Total Recovered'].values[0]), style={'font-weight': '900', 'color': '#70a901', 'font-size': '275%'}), html.P("Total Recovered", style={'color': '#f9f9f9'})]

@app.callback(
    Output('map_graph', 'figure'),
    [Input('countries-dropdown', 'value')])
def zoom_in(value):
    country = countries['{}'.format(value)]
    print('Zoom in val: ', country)

    if country == 'Global':
        return create_map_fig(summary_data, 25, 0)
    
    data = summary_data_province[summary_data_province["Province"] == country]
    return create_map_fig(summary_data, data['latitude'].values[0], data['longitude'].values[0], 3, 40)

@app.callback(
    Output('curve_graph', 'figure'),
    [Input('map_graph', 'clickData'),
    Input('cases-deaths', 'n_clicks'),
    Input('daily-cases-deaths', 'n_clicks')])
def update_fig(hoverData, n_clicks_cum, n_clicks_day):
    ctx = dash.callback_context

    if not ctx.triggered:
        button_id = 'cases-deaths'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    slug = 'Canada'
    if button_id == 'cases-deaths' or button_id == 'map_graph':
        return update_country_cases(hoverData, slug)
    elif button_id == 'daily-cases-deaths':
        return daily_country_data(hoverData, slug)

@app.callback(
    Output('cases_graph', 'figure'),
    [Input('log-cum-conf', 'n_clicks'),
    Input('cum-conf', 'n_clicks'),
    Input('day-conf', 'n_clicks'),
    Input('cases-dist', 'n_clicks')])
def update_graph(logcumconf, cumconf, dayconf, distgraph):
    ctx = dash.callback_context

    if not ctx.triggered:
        button_id = 'cases-dist'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'log-cum-conf':
        return create_confirmed_cases_graph(log_scale = True)
    elif button_id == 'cum-conf':
        return create_confirmed_cases_graph(log_scale = False)
    elif button_id == 'day-conf':
        return create_daily_cases_graph()
    elif button_id == 'cases-dist':
        return get_pie_graph()

@app.callback(
    Output('dist_graphs', 'figure'),
    [Input('test', 'n_clicks'),
    Input('per-milli-cases-death', 'n_clicks'),
    Input('cases-fatalities-ratio', 'n_clicks'),
    Input('map_graph', 'clickData'),
    Input('country-distribution', 'n_clicks')])
def update_graph_2(test, permillicasesdeath, casesfatalitiesratio, hoverData, country_dist_clicks):
    ctx = dash.callback_context

    if not ctx.triggered:
        button_id = 'test'
        value='Canada'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    slug = 'Canada'

    if button_id == 'test' or button_id == 'map_graph':
        return get_testing_graph(hoverData, slug)
    elif button_id == 'per-milli-cases-death':
        return per_million_data(hoverData, slug)
    elif button_id == 'cases-fatalities-ratio':
        return cases_fatalities_ratio(hoverData, slug)
    elif button_id == 'country-distribution':
        return country_pie_dist(hoverData, slug)

@app.callback(
    Output('graph-top', 'children'),
    [Input('top-countries-bar-chart', 'n_clicks'),
    Input('table-cases-death', 'n_clicks')])
def update_graph_3(topcountriesbarchart, tablecasesdeath):
    ctx = dash.callback_context

    if not ctx.triggered:
        button_id = 'top-countries-bar-chart'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'top-countries-bar-chart':
        return top_countries_graph()
    elif button_id == 'table-cases-death':
        return create_confirmed_cases_data_table()

@app.callback(
    Output('news-table', 'children'),
    [Input('map_graph', 'clickData')])
def update_graph_4(hoverData):
    ctx = dash.callback_context

    if not ctx.triggered:
        button_id = 'map_graph'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    slug = 'Canada'
    return getNewsTable(hoverData, slug)

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=80)
