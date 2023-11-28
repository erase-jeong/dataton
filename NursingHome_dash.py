from dash import Dash, html, dash_table, dcc, Input, Output
import pandas as pd
import plotly.express as px
import os
import json
import plotly.graph_objects as go


# 현재 스크립트의 디렉토리 경로 가져오기
script_dir = os.path.dirname(__file__)

# 작업 디렉토리 변경
os.chdir(script_dir)

csv_file_path = "./부산요양시설.csv"

df = pd.read_csv(csv_file_path, encoding='utf-8')
df = df.iloc[1:]
# 필요없는 열 제거
columns_to_drop = ['장기요양기관내역', 'Unnamed: 7', 'Unnamed: 8']
df = df.drop(columns_to_drop, axis=1)

# 열 이름 변경
df = df.drop(1)
df.columns = ['장기요양기관', '급여종류', '평가결과', '정원', '현원', '잔여', '주소', '전화번호']

### 구/군 추출 ###
import re

# 정규식 패턴 설정
pattern = re.compile(r'부산광역시\s*([\w]+[구군읍]?)\s*.*')

# 주소열에서 구/군 추출
df['구/군'] = df['주소'].apply(lambda x: re.search(pattern, str(x)).group(1).strip() if re.search(pattern, str(x)) else None)

# 평가결과 열에서 알파벳만 추출
df['평가결과_간단히'] = df['평가결과'].apply(lambda x: re.search(r'([A-Z])\s*\(', str(x)).group(1) if re.search(r'([A-Z])\s*\(', str(x)) else str(x))


gu_dataframes = {}
for gu in df['구/군'].unique():
    gu_dataframes[gu] = df[df['구/군'] == gu]

ABC_dataframes = {}
for abc in df['평가결과_간단히'].unique():
    ABC_dataframes[abc] = df[df['평가결과_간단히'] == abc]

print(ABC_dataframes['A'])

# 데이터 로드
os.chdir(script_dir)
with open('./hangjeongdong_부산광역시.geojson', 'r') as f:
    busan_geo = json.load(f)

app = Dash(__name__, suppress_callback_exceptions=True)
app.layout = html.Div([
    html.H1(children='부산시 구별 요양시설 분석'),
    dash_table.DataTable(data=df.to_dict('records'), page_size=15),

    html.H2(children='시군구 선택하기'),
    dcc.Dropdown(options=[{'label': i, 'value': i} for i in df['구/군'].unique()], id='dropdown'),
    

    html.H2(children='등급 선택하기'),
    dcc.Checklist(options=[{'label': i, 'value': i} for i in ['A', 'B', 'C', '신설']], id="ABC"),

    html.H2(children='종류 선택하기'),
    dcc.Checklist(options=[{'label': i, 'value': i} for i in ['주야간보호', '방문', '기관']], id="type"),

     html.P(),

    html.Div(id='chk_result2'),

    html.H2("선택한 정보에 대한 요양원 리스트22"),
    dash_table.DataTable(
        id='list_result',
        columns=[{'name': col, 'id': col} for col in df.columns],
        style_table={'overflowX': 'auto'},page_size=7
    ),
    
    html.H2("선택한 정보에 대한 지도 버블차트"),
    dcc.Graph(id='map'),

    html.Div(id='facility-count') 
])


@app.callback(
    Output('list_result','data'),
    Input('dropdown','value'),
    Input('ABC', 'value')        
)

def nursing_home_list(dropdown):
    if dropdown in gu_dataframes:
        return gu_dataframes[dropdown].to_dict('records')
    else:
        return []


@app.callback(
    Output('list_result','data'),
    Input('dropdown','value'),
    Input('ABC', 'value')        
)

def nursing_home_list(dropdown):
    if dropdown in gu_dataframes:
        return gu_dataframes[dropdown].to_dict('records')
    else:
        return []


@app.callback(
    Output('chk_result2', 'children'),
    Input('dropdown', 'value'),
    Input('ABC', 'value'),
    Input('type', 'value')
)
def update_div(dropdown, ABC, type):
    if dropdown and ABC and type:
        return f'선택한 구는 {dropdown}이며, 선택한 등급의 종류는 {ABC}이고, 선택한 급여종류는 {type} 입니다.'
    else:
        return f'군구, 등급 및 급여종류를 선택해주세요.'




@app.callback(
    Output('map', 'figure'),
    Output('facility-count', 'children'),
    Input('dropdown', 'value'),
    Input('ABC', 'value'),
    Input('type', 'value'),
)
def update_map_and_count(dropdown, ABC, type):
    if dropdown and ABC and type:
        filtered_df = df[(df['구/군'] == dropdown) & (df['평가결과_간단히'] == ABC) & (df['급여종류'] == type)]

        if len(filtered_df) > 0:
            # 부산 지도 생성
            map_fig = go.Figure(go.Scattermapbox(
                lat=filtered_df['위도'],  # 요양시설의 위도 정보
                lon=filtered_df['경도'],  # 요양시설의 경도 정보
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=filtered_df['현원'],  # 요양시설의 현원 정보에 따라 마커 크기 변경
                    color=filtered_df['평가결과_간단히'],  # 요양시설의 평가결과에 따라 마커 색상 변경
                ),
                text=filtered_df['장기요양기관'],  # 요양시설의 이름을 마커에 표시
            ))

            map_fig.update_layout(
                mapbox={
                    'style': 'carto-positron',  # 지도 스타일 설정
                    'center': {'lat': 35.1796, 'lon': 129.0756},  # 부산의 중심 좌표
                    'zoom': 10,  # 지도의 확대/축소 정도
                },
                showlegend=False,  # 범례 숨김
                margin={'l': 0, 'r': 0, 't': 0, 'b': 0},  # 여백 설정
                title=f'{dropdown} {ABC} {type} 지도 버블차트'
            )

            # 선택된 조건에 해당하는 요양시설 개수 계산
            count_df = df[(df['구/군'] == dropdown) & (df['평가결과_간단히'] == ABC) & (df['급여종류'] == type)].groupby('구/군').size().reset_index(name='개수')

            # 개수를 막대 그래프로 시각화
            count_fig = px.bar(count_df, x='구/군', y='개수', title='구/군별 요양시설 개수')

            return map_fig, dcc.Graph(figure=count_fig)  # count_fig를 반환하도록 수정

    empty_fig = go.Figure()
    return empty_fig, ''  # 빈 지도와 빈 문자열 반환


if __name__ == '__main__':
    app.run_server(debug=True)
