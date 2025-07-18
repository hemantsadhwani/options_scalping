import pandas as pd
import json
import yaml
from datetime import datetime
from zoneinfo import ZoneInfo

def convert_datetime_to_unix(date_str):
    """Convert various date formats to a Unix timestamp."""
    # Ensure date_str is a string
    date_str = str(date_str).strip()
    
    formats_to_try = [
        '%Y-%m-%d %H:%M:%S',        # Format in put_out.csv
        '%d/%m/%Y %I:%M:%S %p'     # Possible format in trades csv
    ]
    
    dt_naive = None
    for fmt in formats_to_try:
        try:
            dt_naive = datetime.strptime(date_str, fmt)
            break  # If parsing is successful, exit the loop
        except ValueError:
            continue # If parsing fails, try the next format

    if dt_naive is None:
        print(f"Error: Could not parse date '{{date_str}}' with any known format.")
        return None

    try:
        # Make the datetime aware of the IST timezone
        ist = ZoneInfo("Asia/Kolkata")
        dt_aware = dt_naive.replace(tzinfo=ist)
        # Convert to Unix timestamp (which is in UTC)
        return int(dt_aware.timestamp())
    except Exception as e:
        print(f"Error setting timezone or converting to timestamp for '{{date_str}}': {{e}}")
        return None

def process_csv_data():
    """Process the CSV files and prepare data for JavaScript"""
    
    # Read the OHLC data
    ohlc_df = pd.read_csv('tradeview/put_out.csv', header=0)
    ohlc_df['time'] = ohlc_df['datetime'].apply(convert_datetime_to_unix)
    
    # Read the trades data
    trades_df = pd.read_csv('tradeview/put_rev_v1_trades.csv')
    
    # Process OHLC data
    ohlc_data = []
    stoch_k_data = []
    stoch_d_data = []
    williams_r9_data = []
    williams_r28_data = []
    
    for _, row in ohlc_df.iterrows():
        time_val = int(row['time'])
        
        # OHLC data
        ohlc_data.append({
            'time': time_val,
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close'])
        })
        
        # Technical indicators
        stoch_k_data.append({
            'time': time_val,
            'value': float(row['K'])
        })
        
        stoch_d_data.append({
            'time': time_val,
            'value': float(row['D'])
        })
        
        # Williams %R data
        williams_r9_data.append({
            'time': time_val,
            'value': float(row['%R'])
        })
        
        williams_r28_data.append({
            'time': time_val,
            'value': float(row['%R.1'])
        })
        
    # Process trades data
    processed_trades = []
    for index, row in trades_df.iterrows():
        # Entry trade
        processed_trades.append({
            'Trade #': index + 1,
            'Type': 'Entry long',
            'Signal': row['Trade Type'],
            'Date/Time': convert_datetime_to_unix(row['Entry Time']),
            'Price INR': row['Entry Price'],
            'Quantity': 37,  # Assuming a fixed quantity
            'P&L INR': row['P/L'],
            'P&L %': row['P/L %'].replace('%', ''),
            'Run-up INR': 0,
            'Run-up %': 0,
            'Drawdown INR': 0,
            'Drawdown %': 0,
            'Cumulative P&L INR': 0,
            'Cumulative P&L %': 0
        })
        # Exit trade
        processed_trades.append({
            'Trade #': index + 1,
            'Type': 'Exit long',
            'Signal': row['Exit Reason'],
            'Date/Time': convert_datetime_to_unix(row['Exit Time']),
            'Price INR': row['Exit Price'],
            'Quantity': 37, # Assuming a fixed quantity
            'P&L INR': row['P/L'],
            'P&L %': row['P/L %'].replace('%', ''),
            'Run-up INR': 0,
            'Run-up %': 0,
            'Drawdown INR': 0,
            'Drawdown %': 0,
            'Cumulative P&L INR': 0,
            'Cumulative P&L %': 0
        })

    # Convert processed trades to CSV format
    trades_csv_df = pd.DataFrame(processed_trades)
    trades_csv_content = trades_csv_df.to_csv(index=False)
    
    return {
        'ohlc': ohlc_data,
        'stochRSI_K': stoch_k_data,
        'stochRSI': stoch_d_data,
        'williamsR9': williams_r9_data,
        'williamsR28': williams_r28_data,
        'trades_csv': trades_csv_content
    }

def generate_html():
    """Generate the complete HTML file"""
    
    # Process the data
    data = process_csv_data()
    
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TradingView Chart - Enhanced with Trades</title>
    <script src="https://unpkg.com/lightweight-charts@4.0.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            background-color: #131722;
            color: #D9D9D9;
            margin: 0;
            padding: 0;
            display: flex;
            height: 100vh;
        }}
        
        #main-container {{
            display: flex;
            width: 100%;
            height: 100%;
        }}
        
        #chart-section {{
            flex: 1;
            display: flex;
            flex-direction: column;
            min-width: 0;
        }}
        
        #chart-container {{
            flex-grow: 1;
            display: flex;
            flex-direction: column;
        }}
        
        .chart-pane {{
            position: relative;
        }}
        
        #trades-panel {{
            width: 350px;
            background-color: #1E222D;
            border-left: 1px solid #2A2E39;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        
        #trades-header {{
            padding: 12px 16px;
            background-color: #2A2E39;
            border-bottom: 1px solid #363A45;
            font-weight: 600;
            font-size: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        #toggle-trades {{
            background: none;
            border: none;
            color: #D9D9D9;
            cursor: pointer;
            font-size: 16px;
            padding: 4px;
            border-radius: 4px;
        }}
        
        #toggle-trades:hover {{
            background-color: #363A45;
        }}
        
        #trades-content {{
            flex: 1;
            overflow-y: auto;
            padding: 8px;
        }}
        
        .trade-item {{
            background-color: #2A2E39;
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 8px;
            border-left: 4px solid;
        }}
        
        .trade-entry {{
            border-left-color: #26A69A;
        }}
        
        .trade-exit {{
            border-left-color: #EF5350;
        }}
        
        .trade-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        
        .trade-type {{
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
        }}
        
        .trade-entry .trade-type {{
            color: #26A69A;
        }}
        
        .trade-exit .trade-type {{
            color: #EF5350;
        }}
        
        .trade-signal {{
            font-size: 11px;
            color: #B2B5BE;
            background-color: #363A45;
            padding: 2px 6px;
            border-radius: 3px;
        }}
        
        .trade-details {{
            font-size: 11px;
            color: #B2B5BE;
            line-height: 1.4;
        }}
        
        .trade-price {{
            color: #D9D9D9;
            font-weight: 600;
        }}
        
        .trade-pnl {{
            font-weight: 600;
        }}
        
        .trade-pnl.positive {{
            color: #26A69A;
        }}
        
        .trade-pnl.negative {{
            color: #EF5350;
        }}
        
        #legend {{
            position: absolute;
            top: 12px;
            left: 12px;
            z-index: 1000;
            background-color: rgba(255, 255, 255, 0.2);
            padding: 8px;
            border-radius: 4px;
            font-size: 14px;
            pointer-events: none;
            display: none;
        }}
        
        #error-container {{
            color: orange;
            font-size: 16px;
            margin: 12px;
            min-height: 120px;
            overflow-y: auto;
            border: 1px solid orange;
            padding: 10px;
            border-radius: 8px;
            background-color: #ff96000d;
            display: none;
        }}
        
        .marker-tooltip {{
            position: absolute;
            background-color: #2A2E39;
            border: 1px solid #363A45;
            border-radius: 6px;
            padding: 10px;
            font-size: 11px;
            z-index: 1001;
            pointer-events: none;
            display: none;
            max-width: 250px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            line-height: 1.4;
        }}
        
        .marker-tooltip div {{
            margin-bottom: 2px;
        }}
        
        .marker-tooltip div:last-child {{
            margin-bottom: 0;
        }}
        
        @media (max-width: 768px) {{
            #main-container {{
                flex-direction: column;
            }}
            
            #trades-panel {{
                width: 100%;
                height: 200px;
                border-left: none;
                border-top: 1px solid #2A2E39;
            }}
        }}
    </style>
</head>
<body>
    <div id="main-container">
        <div id="chart-section">
            <div id="chart-container">
                <div id="main-chart-container" class="chart-pane"></div>
                <div id="stoch-chart-container" class="chart-pane"></div>
                <div id="williams9-chart-container" class="chart-pane"></div>
                <div id="williams28-chart-container" class="chart-pane"></div>
            </div>
            <div id="legend"></div>
            <div id="error-container"></div>
        </div>
        
        <div id="trades-panel">
            <div id="trades-header">
                <span>List of Trades</span>
                <button id="toggle-trades" title="Toggle trades panel">−</button>
            </div>
            <div id="trades-content">
                <!-- Trades will be populated here -->
            </div>
        </div>
    </div>
    
    <div class="marker-tooltip" id="marker-tooltip"></div>

    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        const data = {json.dumps(data, indent=8).replace('    ', '        ')};

        // Raw CSV data for trades
        const tradesCsvData = `{data['trades_csv']}`;


        const chartOptions = {{
            layout: {{
                background: {{ type: 'solid', color: '#131722' }},
                textColor: '#D9D9D9',
            }},
            grid: {{
                vertLines: {{ color: '#2A2E39' }},
                horzLines: {{ color: '#2A2E39' }},
            }},
            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
            }},
            rightPriceScale: {{
                borderColor: '#485158',
            }},
            timeScale: {{
                borderColor: '#485158',
                timeVisible: true,
                secondsVisible: false,
                tickMarkFormatter: (time, tickMarkType, locale) => {{
                    const date = new Date(time * 1000);
                    return date.toLocaleTimeString('en-IN', {{ hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' }});
                }},
            }},
        }};

        const mainChartContainer = document.getElementById('main-chart-container');
        const stochChartContainer = document.getElementById('stoch-chart-container');
        const williams9ChartContainer = document.getElementById('williams9-chart-container');
        const williams28ChartContainer = document.getElementById('williams28-chart-container');
        const legend = document.getElementById('legend');
        const errorContainer = document.getElementById('error-container');
        const tradesContent = document.getElementById('trades-content');
        const toggleTradesButton = document.getElementById('toggle-trades');
        const tradesPanel = document.getElementById('trades-panel');
        const markerTooltip = document.getElementById('marker-tooltip');

        function displayError(message) {{
            errorContainer.textContent = `Error: ${{message}}`;
            errorContainer.style.display = 'block';
        }}

        // Function to parse CSV data
        function parseCsv(csv) {{
            const lines = csv.trim().split('\\n');
            const headers = lines[0].split(',').map(header => header.trim());
            const result = [];

            for (let i = 1; i < lines.length; i++) {{
                const values = lines[i].split(',').map(value => value.trim());
                if (values.length === headers.length) {{
                    const obj = {{}};
                    headers.forEach((header, index) => {{
                        obj[header] = values[index];
                    }});
                    result.push(obj);
                }}
            }}
            return result;
        }}

        // Function to convert timestamp to Unix timestamp
        function convertDateTimeToUnix(dateTimeStr) {{
            // If it's already a number (synthetic timestamp), return as is
            if (typeof dateTimeStr === 'number') {{
                return dateTimeStr;
            }}
            // If it's a string, try to parse it
            if (typeof dateTimeStr === 'string') {{
                // Check if it's a pure number string
                const numValue = parseFloat(dateTimeStr);
                if (!isNaN(numValue)) {{
                    return numValue;
                }}
                // Otherwise try to parse as date
                const date = new Date(dateTimeStr);
                return date.getTime() / 1000;
            }}
            return dateTimeStr;
        }}

        try {{
            const totalHeight = document.getElementById('chart-container').clientHeight;
            const mainChartHeight = Math.floor(totalHeight * 0.55);
            const indicatorHeight = Math.floor(totalHeight * 0.15);

            const mainChart = LightweightCharts.createChart(mainChartContainer, {{ ...chartOptions, height: mainChartHeight, width: mainChartContainer.clientWidth }});
            const candleSeries = mainChart.addCandlestickSeries({{
                upColor: '#26A69A', downColor: '#EF5350',
                borderDownColor: '#EF5350', borderUpColor: '#26A69A',
                wickDownColor: '#EF5350', wickUpColor: '#26A69A',
            }});
            candleSeries.setData(data.ohlc);

            const stochChart = LightweightCharts.createChart(stochChartContainer, {{
                ...chartOptions,
                height: indicatorHeight,
                width: stochChartContainer.clientWidth,
                watermark: {{ color: 'rgba(255, 255, 255, 0.4)', visible: true, text: 'StochRSI (K,D)', fontSize: 16, horzAlign: 'left', vertAlign: 'top' }},
                timeScale: {{
                    ...chartOptions.timeScale,
                    visible: false,
                }},
            }});
            const stochSeriesD = stochChart.addLineSeries({{ color: '#26A69A', lineWidth: 2, title: 'D' }});
            const stochSeriesK = stochChart.addLineSeries({{ color: '#EF5350', lineWidth: 2, title: 'K' }});
            stochSeriesD.setData(data.stochRSI);
            stochSeriesK.setData(data.stochRSI_K);

            const williams9Chart = LightweightCharts.createChart(williams9ChartContainer, {{
                ...chartOptions,
                height: indicatorHeight,
                width: williams9ChartContainer.clientWidth,
                watermark: {{ color: 'rgba(255, 255, 255, 0.4)', visible: true, text: 'Williams %R (9)', fontSize: 16, horzAlign: 'left', vertAlign: 'top' }},
                timeScale: {{
                    ...chartOptions.timeScale,
                    visible: false,
                }},
            }});
            const williams9Series = williams9Chart.addLineSeries({{ color: '#2196F3', lineWidth: 2 }});
            williams9Series.setData(data.williamsR9);

            const williams28Chart = LightweightCharts.createChart(williams28ChartContainer, {{
                ...chartOptions,
                height: indicatorHeight,
                width: williams28ChartContainer.clientWidth,
                watermark: {{ color: 'rgba(255, 255, 255, 0.4)', visible: true, text: 'Williams %R (28)', fontSize: 16, horzAlign: 'left', vertAlign: 'top' }},
                timeScale: {{
                    ...chartOptions.timeScale,
                    visible: false,
                }},
            }});
            const williams28Series = williams28Chart.addLineSeries({{ color: '#FF9800', lineWidth: 2 }});
            williams28Series.setData(data.williamsR28);

            const ohlcMap = new Map(data.ohlc.map(d => [d.time, d]));
            const stochMapD = new Map(data.stochRSI.map(d => [d.time, d.value]));
            const stochMapK = new Map(data.stochRSI_K.map(d => [d.time, d.value]));
            const williams9Map = new Map(data.williamsR9.map(d => [d.time, d.value]));
            const williams28Map = new Map(data.williamsR28.map(d => [d.time, d.value]));

            function updateLegend(param) {{
                if (!param.time || !param.point) {{
                    legend.style.display = 'none';
                    return;
                }}
                const ohlcData = ohlcMap.get(param.time);
                const stochD = stochMapD.get(param.time);
                const stochK = stochMapK.get(param.time);
                const will9 = williams9Map.get(param.time);
                const will28 = williams28Map.get(param.time);
                if (!ohlcData) {{
                    legend.style.display = 'none';
                    return;
                }}
                legend.style.display = 'block';
                legend.innerHTML = `
                    <div><strong>O:</strong> ${{ohlcData.open.toFixed(2)}} <strong>H:</strong> ${{ohlcData.high.toFixed(2)}} <strong>L:</strong> ${{ohlcData.low.toFixed(2)}} <strong>C:</strong> ${{ohlcData.close.toFixed(2)}}</div>
                    <div style="color: #EF5350;"><strong>Stoch K:</strong> ${{stochK !== undefined ? stochK.toFixed(2) : 'N/A'}}</div>
                    <div style="color: #26A69A;"><strong>Stoch D:</strong> ${{stochD !== undefined ? stochD.toFixed(2) : 'N/A'}}</div>
                    <div style="color: #2196F3;"><strong>Will %R(9):</strong> ${{will9 !== undefined ? will9.toFixed(2) : 'N/A'}}</div>
                    <div style="color: #FF9800;"><strong>Will %R(28):</strong> ${{will28 !== undefined ? will28.toFixed(2) : 'N/A'}}</div>
                `;
            }}

            const charts = [mainChart, stochChart, williams9Chart, williams28Chart];
            charts.forEach(chart => {{
                chart.timeScale().subscribeVisibleLogicalRangeChange(range => {{
                    charts.forEach(otherChart => {{
                        if (chart !== otherChart) {{
                            otherChart.timeScale().setVisibleLogicalRange(range);
                        }}
                    }});
                }});
                chart.subscribeCrosshairMove(updateLegend);
            }});

            new ResizeObserver(() => {{
                const totalHeight = document.getElementById('chart-container').clientHeight;
                const mainChartHeight = Math.floor(totalHeight * 0.55);
                const indicatorHeight = Math.floor(totalHeight * 0.15);
                const width = mainChartContainer.clientWidth;

                mainChart.applyOptions({{ height: mainChartHeight, width }});
                stochChart.applyOptions({{ height: indicatorHeight, width }});
                williams9Chart.applyOptions({{ height: indicatorHeight, width }});
                williams28Chart.applyOptions({{ height: indicatorHeight, width }});
            }}).observe(document.getElementById('chart-container'));

            // Populate trades panel and add markers
            const trades = parseCsv(tradesCsvData);
            const markers = [];

            trades.forEach(trade => {{
                const tradeItem = document.createElement('div');
                tradeItem.classList.add('trade-item');
                
                const tradeTypeClass = trade.Type.toLowerCase().includes('entry') ? 'trade-entry' : 'trade-exit';
                tradeItem.classList.add(tradeTypeClass);

                const pnlValue = parseFloat(trade['P&L %']);
                const pnlClass = pnlValue >= 0 ? 'positive' : 'negative';

                const timestamp = parseFloat(trade['Date/Time']);
                const tradeDateTime = !isNaN(timestamp) ?
                                    new Date(timestamp * 1000).toLocaleString('en-IN', {{ timeZone: 'Asia/Kolkata' }}) :
                                    'Synthetic Trade Time';
                
                tradeItem.innerHTML = `
                    <div class="trade-header">
                        <span class="trade-type">Trade #${{trade['Trade #']}} - ${{trade.Type}}</span>
                        <span class="trade-signal">${{trade.Signal}}</span>
                    </div>
                    <div class="trade-details">
                        <div><strong>Time:</strong> ${{tradeDateTime}}</div>
                        <div><strong>Price:</strong> <span class="trade-price">₹${{trade['Price INR']}}</span></div>
                        <div><strong>P&L:</strong> <span class="trade-pnl ${{pnlClass}}">₹${{trade['P&L INR']}} (${{trade['P&L %']}}%)</span></div>
                    </div>
                `;
                tradesContent.appendChild(tradeItem);

                // Add markers to the chart
                const tradeTime = convertDateTimeToUnix(trade['Date/Time']);
                const tradePrice = parseFloat(trade['Price INR']);

                if (!isNaN(tradeTime) && !isNaN(tradePrice)) {{
                    let markerShape;
                    let markerColor;
                    let markerPosition;
                    let markerText;

                    if (trade.Type.toLowerCase().includes('entry')) {{
                        markerShape = 'arrowUp';
                        markerColor = '#26A69A'; // Green for entry
                        markerPosition = 'belowBar';
                        markerText = 'Entry long';
                    }} else if (trade.Type.toLowerCase().includes('exit')) {{
                        markerShape = 'arrowDown';
                        markerPosition = 'aboveBar';
                        markerText = trade.Signal; // Use the exit reason as text
                        
                        // Different colors based on exit signal
                        if (trade.Signal.toLowerCase().includes('profit')) {{
                            markerColor = '#26A69A'; // Green for profit
                        }} else if (trade.Signal.toLowerCase().includes('stop') || trade.Signal.toLowerCase().includes('loss')) {{
                            markerColor = '#EF5350'; // Red for stop loss
                        }} else {{
                            markerColor = '#FF9800'; // Orange for other exits
                        }}
                    }}

                    if (markerShape) {{
                        markers.push({{
                            time: tradeTime,
                            position: markerPosition,
                            color: markerColor,
                            shape: markerShape,
                            text: markerText,
                            size: 1, // Use size 1 for line-style arrows
                            tradeInfo: trade // Store full trade info for tooltip
                        }});
                    }}
                }}
            }});

            candleSeries.setMarkers(markers);

            // Marker tooltip functionality
            function updateMarkerTooltip(param) {{
                if (param.point) {{
                    // Find the corresponding time for the crosshair position
                    const time = param.time;
                    if (!time) {{
                        markerTooltip.style.display = 'none';
                        return;
                    }}

                    const marker = markers.find(m => m.time === time);
                    if (marker && marker.tradeInfo) {{
                        const trade = marker.tradeInfo;
                        const pnlValue = parseFloat(trade['P&L %']);
                        const pnlClass = pnlValue >= 0 ? 'positive' : 'negative';
                        const tradeTypeColor = trade.Type.toLowerCase().includes('entry') ? '#26A69A' :
                                             (trade.Signal.toLowerCase().includes('profit') ? '#26A69A' : '#EF5350');
                        
                        const timestamp = parseFloat(trade['Date/Time']);
                        const tradeDateTime = !isNaN(timestamp) ?
                                            new Date(timestamp * 1000).toLocaleString('en-IN', {{ timeZone: 'Asia/Kolkata' }}) :
                                            'Synthetic Trade Time';

                        markerTooltip.innerHTML = `
                            <div style="color: ${{tradeTypeColor}}; font-weight: bold; margin-bottom: 4px;">
                                ${{trade.Type.toUpperCase()}} - ${{trade.Signal}}
                            </div>
                            <div><strong>Trade #:</strong> ${{trade['Trade #']}}</div>
                            <div><strong>Time:</strong> ${{tradeDateTime}}</div>
                            <div><strong>Price:</strong> ₹${{trade['Price INR']}}</div>
                            <div><strong>P&L:</strong> <span class="${{pnlClass}}">₹${{trade['P&L INR']}} (${{trade['P&L %']}}%)</span></div>
                        `;
                        markerTooltip.style.display = 'block';
                        markerTooltip.style.left = `${{param.point.x + 15}}px`;
                        markerTooltip.style.top = `${{param.point.y + 15}}px`;
                    }} else {{
                        markerTooltip.style.display = 'none';
                    }}
                }} else {{
                    markerTooltip.style.display = 'none';
                }}
            }}

            // Subscribe the tooltip function to all charts
            charts.forEach(chart => {{
                chart.subscribeCrosshairMove(updateMarkerTooltip);
            }});

            // Toggle trades panel
            let tradesPanelVisible = true;
            toggleTradesButton.addEventListener('click', () => {{
                if (tradesPanelVisible) {{
                    tradesPanel.style.width = '0';
                    tradesPanel.style.borderLeft = 'none';
                    toggleTradesButton.textContent = '+';
                    toggleTradesButton.title = 'Show trades panel';
                }} else {{
                    tradesPanel.style.width = '350px';
                    tradesPanel.style.borderLeft = '1px solid #2A2E39';
                    toggleTradesButton.textContent = '−';
                    toggleTradesButton.title = 'Hide trades panel';
                }}
                tradesPanelVisible = !tradesPanelVisible;
                // Trigger chart resize after panel toggle
                window.dispatchEvent(new Event('resize'));
            }});


        }} catch (e) {{
            displayError(e.message);
            console.error(e);
        }}
    }});
    </script>
</body>
</html>'''
    
    return html_content

def main():
    """Main function to generate the HTML file"""
    try:
        print("Processing CSV files...")
        html_content = generate_html()
        
        print("Writing HTML file...")
        with open('tradeview/NSE_NIFTY250717P25200.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print("HTML file 'tradeview/NSE_NIFTY250717P25200.html' has been created successfully!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
