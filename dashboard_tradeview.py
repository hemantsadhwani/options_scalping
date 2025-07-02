import dash
from dash import dcc, html
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import pytz

app = dash.Dash(__name__)

try:
    df = pd.read_csv('tradeview_utc.csv')
    df = df[df['datetime'] != 'datetime']
    df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
    df = df.dropna(subset=['datetime'])
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    ist = pytz.timezone('Asia/Kolkata')
    df['time_ist'] = df['time'].dt.tz_convert(ist)
    df = df[
        (df['time_ist'].dt.time >= pd.to_datetime('09:15').time()) &
        (df['time_ist'].dt.time <= pd.to_datetime('15:30').time())
    ]
    df = df.sort_values('time_ist')

    df['Up Trend'] = pd.to_numeric(df['Up Trend'], errors='coerce')
    df['Down Trend'] = pd.to_numeric(df['Down Trend'], errors='coerce')

    # Create supertrend series: Up Trend where available, else Down Trend
    supertrend = df['Up Trend'].combine_first(df['Down Trend'])

    # Determine color segments for supertrend line
    colors = ['green' if not pd.isna(u) else 'red' for u in df['Up Trend']]
    segments = []
    start_idx = 0
    current_color = colors[0]

    for i in range(1, len(colors)):
        if colors[i] != current_color:
            segments.append((start_idx, i - 1, current_color))
            start_idx = i
            current_color = colors[i]
    segments.append((start_idx, len(colors) - 1, current_color))

    # Create subplots with 4 rows
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.5, 0.15, 0.15, 0.15],
        subplot_titles=(
            'OHLC with Supertrend & CPR Levels',
            'Stochastic RSI',
            'Williams %R(9)',
            'Williams %R(28)'
        )
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df['time_ist'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='OHLC'
        ),
        row=1, col=1
    )

    # Plot supertrend segments
    for start, end, color in segments:
        fig.add_trace(
            go.Scatter(
                x=df['time_ist'].iloc[start:end+1],
                y=supertrend.iloc[start:end+1],
                mode='lines',
                line=dict(color=color, width=3),
                name='Supertrend',
                showlegend=False
            ),
            row=1, col=1
        )

    # CPR lines
    cpr_columns = ['Daily Pivot', 'Daily BC', 'Daily TC']
    support_columns = ['Daily S1', 'Daily S2', 'Daily S3', 'Daily S4']
    resistance_columns = ['Daily R1', 'Daily R2', 'Daily R3', 'Daily R4']
    prev_day_columns = ['Prev Day High', 'Prev Day Low']

    for col in cpr_columns:
        if col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['time_ist'],
                    y=df[col],
                    mode='lines',
                    name=col,
                    line=dict(color='blue', width=2, dash='dot'),
                    connectgaps=False,
                    showlegend=True
                ),
                row=1, col=1
            )
    for col in support_columns:
        if col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['time_ist'],
                    y=df[col],
                    mode='lines',
                    name=col,
                    line=dict(color='red', width=2, dash='dot'),
                    connectgaps=False,
                    showlegend=True
                ),
                row=1, col=1
            )
    for col in resistance_columns:
        if col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['time_ist'],
                    y=df[col],
                    mode='lines',
                    name=col,
                    line=dict(color='purple', width=2, dash='dot'),
                    connectgaps=False,
                    showlegend=True
                ),
                row=1, col=1
            )
    for col in prev_day_columns:
        if col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['time_ist'],
                    y=df[col],
                    mode='lines',
                    name=col,
                    line=dict(color='black', width=2, dash='dot'),
                    connectgaps=False,
                    showlegend=True
                ),
                row=1, col=1
            )

    # Stochastic RSI
    if 'K' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['time_ist'],
                y=df['K'],
                mode='lines',
                name='Stoch RSI %K',
                line=dict(color='#2E86AB', width=2),
                yaxis='y2'
            ),
            row=2, col=1
        )
    if 'D' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['time_ist'],
                y=df['D'],
                mode='lines',
                name='Stoch RSI %D',
                line=dict(color='#F24236', width=2),
                yaxis='y2'
            ),
            row=2, col=1
        )

    # Horizontal reference lines for Stochastic RSI
    fig.add_hline(y=80, line_dash="dash", line_color="rgba(255,0,0,0.5)", row=2, col=1, annotation_text="80")
    fig.add_hline(y=50, line_dash="dot", line_color="rgba(128,128,128,0.5)", row=2, col=1, annotation_text="50")
    fig.add_hline(y=20, line_dash="dash", line_color="rgba(0,128,0,0.5)", row=2, col=1, annotation_text="20")

    # Williams %R(9)
    if '%R' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['time_ist'],
                y=df['%R'],
                mode='lines',
                name='Williams %R(9)',
                line=dict(color='blue', width=2)
            ),
            row=3, col=1
        )
        fig.add_hline(y=-20, line_dash="dash", line_color="rgba(255,0,0,0.5)", row=3, col=1, annotation_text="-20")
        fig.add_hline(y=-50, line_dash="dot", line_color="rgba(128,128,128,0.5)", row=3, col=1, annotation_text="-50")
        fig.add_hline(y=-80, line_dash="dash", line_color="rgba(0,128,0,0.5)", row=3, col=1, annotation_text="-80")
        fig.update_yaxes(title_text="Williams %R(9)", range=[-100, 0], row=3, col=1, showgrid=True, gridcolor='rgba(128,128,128,0.2)')

    # Williams %R(28)
    if '%R.1' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['time_ist'],
                y=df['%R.1'],
                mode='lines',
                name='Williams %R(28)',
                line=dict(color='orange', width=2)
            ),
            row=4, col=1
        )
        fig.add_hline(y=-20, line_dash="dash", line_color="rgba(255,0,0,0.5)", row=4, col=1, annotation_text="-20")
        fig.add_hline(y=-50, line_dash="dot", line_color="rgba(128,128,128,0.5)", row=4, col=1, annotation_text="-50")
        fig.add_hline(y=-80, line_dash="dash", line_color="rgba(0,128,0,0.5)", row=4, col=1, annotation_text="-80")
        fig.update_yaxes(title_text="Williams %R(28)", range=[-100, 0], row=4, col=1, showgrid=True, gridcolor='rgba(128,128,128,0.2)')

    # Rangebreaks for weekends and non-trading hours
    rangebreaks = [dict(bounds=[6, 1], pattern="day of week")]
    unique_dates = sorted(df['time_ist'].dt.date.unique())
    for i in range(len(unique_dates) - 1):
        current_date = unique_dates[i]
        next_date = unique_dates[i + 1]
        break_start = f"{current_date} 15:30:00+05:30"
        break_end = f"{next_date} 09:15:00+05:30"
        rangebreaks.append(dict(bounds=[break_start, break_end]))

    date_range_str = f"{unique_dates[0]} to {unique_dates[-1]}" if len(unique_dates) > 1 else str(unique_dates[0])

    fig.update_layout(
        title=f'Supertrend with CPR Levels Visualization ({date_range_str})',
        height=1200,
        template='plotly_white',
        showlegend=True,
        xaxis_rangeslider_visible=False,
        xaxis=dict(rangebreaks=rangebreaks)
    )

    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Stoch RSI", range=[0, 100], row=2, col=1, showgrid=True, gridcolor='rgba(128,128,128,0.2)')
    fig.update_xaxes(title_text="Time (IST)", row=2, col=1)
    fig.update_xaxes(title_text="Time (IST)", row=3, col=1)
    fig.update_xaxes(title_text="Time (IST)", row=4, col=1)
    fig.update_xaxes(rangebreaks=rangebreaks)

    data_loaded = True
    error_message = ""
    data_info = f"Loaded {len(df)} data points from {date_range_str}"

except Exception as e:
    data_loaded = False
    error_message = str(e)
    fig = go.Figure()
    data_info = "Error loading data"

app.layout = html.Div([
    html.H1("Supertrend with CPR Levels Visualization", style={'textAlign': 'center', 'marginBottom': 30}),
    html.Div([
        html.H4(f"📊 {data_info}", style={'color': 'green', 'textAlign': 'center'})
    ]) if data_loaded else html.Div(),
    html.Div([
        html.H3("Error:", style={'color': 'red'}) if not data_loaded else "",
        html.P(error_message, style={'color': 'red'}) if not data_loaded else ""
    ]) if not data_loaded else html.Div(),
    dcc.Graph(
        id='supertrend-cpr-chart',
        figure=fig,
        style={'height': '1200px'}
    ) if data_loaded else html.Div(),
])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8050)