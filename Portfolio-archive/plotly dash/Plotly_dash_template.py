#following along from the docs.


import dash
from dash import html, dcc
import pandas as pd
import numpy as np
import plotly.express as px
from dash.dependencies import Input, Output

#code snippet to change directories
# import os
# path_new = r'filepath_to_your_desired_file' # use your path
# os.chdir(path_new) #change directory

#which file do you want to read in?
df = pd.read_csv("csv_you_want")

#prepare the dataframe
df2=df.drop(columns = ['columns_you_dont_want'])

#do the rest of the EDA and then melt it up into the categories you want.
df2 = pd.melt(df2, id_vars =['Date/Time'], value_vars=['whatever_you_like']).sort_values(by=['Date/Time', 'variable'], ascending = ['True', 'True'], ignore_index = 'True')
df2['Date/Time'] = df2['Date/Time'].replace(to_replace=r'_', value = ' ', regex = True)
df2['value'].replace('-', np.nan, inplace=True) #purposely throwing out rows with dashes
df2.rename(columns={"Date/Time": "date_time"}, inplace = True) #as an example of some renaming you might need to do.

df2['value'] = df2['value'].astype('float64') #making sure (in this example) all the data is classed as float, so that the yaxis on the graphs will sort well.
#df = df.groupby(['Date/Time'])
df2=df2.fillna("") # otherwise creates issues w MySQL; fill empty areas whatever they are with NaN
df2['date_time'].replace('', np.nan, inplace=True) #purposely throwing out empty rows, in this example, for date time column.
df2 = df2.reset_index(drop=True)


#creating labels for the various datapoints
datapoints = df2['variable'].unique() #simply create a unique list of datapoints
labels =[{'label':i, 'value':i} for i in datapoints] #you have to use the keyword label. 

fig = px.line(df2, x ='date_time', y='value')

app = dash.Dash()
app.layout = html.Div([html.Div(), #div means the start of a new section
			 html.H1('Big title you want'),
			 html.H3('Refresh the page when you have new data in your csv; the graph updates'),
			 html.Div(dcc.Dropdown(id='dropdown', options = labels)), #you have to use label - value pairs per syntax. In this case ours is called 'labels'. 
			 dcc.Graph(id='fig1', figure=fig)]) #figure = fig is also part of the syntax.

@app.callback(Output('fig1', 'figure'),
				Input('dropdown', 'value')) #so here we're linking dropdown value (per user selection) to what graph we want shown.

def update_graph(state):
	df_state = df2.loc[df2['variable'] == state]
	fig = px.scatter(df_state, x= 'date_time', y='value', title = f'{state} values with time')
	return fig

app.run_server(debug=True, port=8056) #allows you to refresh the webpage and see updated code. I've put port 8056 because it's not a default port, so it won't interrupt whatever else you're running. Of course you can pick any port.

