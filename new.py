import numpy as np
import pandas as pd
import string
import requests
import matplotlib
import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import re
import dash_table
import time

while True:
                                     
    dfs = pd.read_html ('https://br.tradingview.com/markets/stocks-brazilia/market-movers-active/', decimal=".",thousands=",")
    df = dfs[0]
    df=df.head(15)

    # renomeia as colunas
    df.rename (columns={'Unnamed: 0':'Nome'}, inplace=True )
    df.rename (columns={'Unnamed: 1':'Preço'}, inplace=True )
    df.rename (columns={'Unnamed: 2':'Var%'}, inplace=True )
    df.rename (columns={'Unnamed: 3':'Oscilação'}, inplace=True )
    df.rename (columns={'Unnamed: 4':'Classificação'}, inplace=True )
    df.rename (columns={'Unnamed: 5':'Volume'}, inplace=True )
    df.rename (columns={'Unnamed: 6':'Mercado'}, inplace=True )
    df.rename (columns={'Unnamed: 7':'Lucro'}, inplace=True )
    df.rename (columns={'Unnamed: 8':'EPS'}, inplace=True )
    df.rename (columns={'Unnamed: 9':'Funcionarios'}, inplace=True )
    df.rename (columns={'Unnamed: 10':'Setor'}, inplace=True )

    #remove as colunas que nao quero utilizar
    df.drop('Mercado', axis=1, inplace=True)
    df.drop('Lucro', axis=1, inplace=True)
    df.drop('EPS', axis=1, inplace=True)
    df.drop('Funcionarios', axis=1, inplace=True)
    df['Oscilação'] = df['Oscilação'].astype(float)

    ## Execute a conversão de dados usando ferramentas de processamento de string, remove % e M
    df['Volume'] = list(map(lambda x: x[:-1], df['Volume'].values))
    df['Var%'] = list(map(lambda x: x[:-1], df['Var%'].values))

    ##Converter dados em formato numérico
    df['Volume'] = [float(x) for x in df['Volume'].values]
    df['Var%'] = [float(x) for x in df['Var%'].values]

    # transforma volume M em Milhoes
    df['Volume'] = df['Volume']*1000000

    # Fatia a Coluna Name e peha apenas o Ticker e cria uma coluna nova apenas com o simbolo da acao

    def fix_names(coluna):
        
        my_results = list()
        
        for col in coluna:
            try:
                name = re.findall('[A-Z]{4}\d{1,2}',col)[0]
                
            except:
                
                try:
                    name = re.findall('[A-Z]\d[A-Z]{2}\d',col)[0]
                except:
                    name = 'NA'
            
            my_results.append(name)
            
        return my_results

    fix_names(df['Nome'])
    #df ['Ticker'] = fix_names(df['Nome'])
    df ['Nome'] = fix_names(df['Nome'])
    df.drop('Volume', axis=1, inplace=True)

    

    # DASH
    app = dash.Dash(__name__)

    PAGE_SIZE = 5

    app.layout = html.Div(
        
        className="row",
        children=[ html.H1(children='As 15 ações mais negociadas na B3 atualizadas a cada 20 minutos '),
        html.Div(children=''''''),
            html.Div(
                dash_table.DataTable(
                    id='table-paging-with-graph',
                    columns=[
                        {"name": i, "id": i} for i in sorted(df.columns)
                    ],
                    page_current=0,
                    page_size=20,
                    page_action='custom',

                    filter_action='custom',
                    filter_query='',

                    sort_action='custom',
                    sort_mode='multi',
                    sort_by=[]
                ),
                # style={'height': 850, 'overflowY': 'scroll'},
                # className='five columns'
                
            ),
            html.H1(children='Graficos'),
            html.Div(
                id='table-paging-with-graph-container',
                className="five columns"
            )
        ]
    )

    operators = [['ge ', '>='],
                ['le ', '<='],
                ['lt ', '<'],
                ['gt ', '>'],
                ['ne ', '!='],
                ['eq ', '='],
                ['contains '],
                ['datestartswith ']]


    def split_filter_part(filter_part):
        for operator_type in operators:
            for operator in operator_type:
                if operator in filter_part:
                    name_part, value_part = filter_part.split(operator, 1)
                    name = name_part[name_part.find('{') + 1: name_part.rfind('}')]

                    value_part = value_part.strip()
                    v0 = value_part[0]
                    if (v0 == value_part[-1] and v0 in ("'", '"', '`')):
                        value = value_part[1: -1].replace('\\' + v0, v0)
                    else:
                        try:
                            value = float(value_part)
                        except ValueError:
                            value = value_part

                    # operadores de palavras precisam de espaços após eles na string de filtro,
                    return name, operator_type[0].strip(), value

        return [None] * 3


    @app.callback(
        Output('table-paging-with-graph', "data"),
        Input('table-paging-with-graph', "page_current"),
        Input('table-paging-with-graph', "page_size"),
        Input('table-paging-with-graph', "sort_by"),
        Input('table-paging-with-graph', "filter_query"))
    def update_table(page_current, page_size, sort_by, filter):
        filtering_expressions = filter.split(' && ')
        dff = df
        for filter_part in filtering_expressions:
            col_name, operator, filter_value = split_filter_part(filter_part)

            if operator in ('eq', 'ne', 'lt', 'le', 'gt', 'ge'):
                # esses operadores correspondem aos nomes dos métodos dos operadores da série pandas
                dff = dff.loc[getattr(dff[col_name], operator)(filter_value)]
            elif operator == 'contains':
                dff = dff.loc[dff[col_name].str.contains(filter_value)]
            elif operator == 'datestartswith':
               # esta é uma simplificação da lógica de filtragem de front-end,
                 # só funciona com campos completos no formato padrão
                dff = dff.loc[dff[col_name].str.startswith(filter_value)]

        if len(sort_by):
            dff = dff.sort_values(
                [col['column_id'] for col in sort_by],
                ascending=[
                    col['direction'] == 'asc'
                    for col in sort_by
                ],
                inplace=False
            )

        return dff.iloc[
            page_current*page_size: (page_current + 1)*page_size
        ].to_dict('records')


    @app.callback(
        Output('table-paging-with-graph-container', "children"),
        Input('table-paging-with-graph', "data"))
    def update_graph(rows):
        dff = pd.DataFrame(rows)
        return html.Div(
            [
                dcc.Graph(
                    id=column,
                    figure={
                        "data": [
                            {
                                "x": dff["Nome"],
                                "y": dff[column] if column in dff else [],
                                "type": "bar",
                                "marker": {"color": "#0074D9"},
                            }
                        ],
                        "layout": {
                            "xaxis": {"automargin": True},
                            "yaxis": {"automargin": True},
                            "height": 300,
                            "margin": {"t": 10, "l": 10, "r": 10},
                        },
                    },
                )
                for column in ["Classificação", "Oscilação", "Preço"]
            ]
        )


    if __name__ == '__main__':
        app.run_server(debug=True)

time.sleep(1200) #A cada 20 MIN ele executa o print