import pandas as pd
import os
from datetime import datetime, timedelta
import glob
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

def get_weekly_groups(date_folders):
    """Group dates into weekly cycles (Friday to Thursday)"""
    # Convert date strings to datetime objects
    dates_with_obj = []
    for date_str in date_folders:
        try:
            # Parse ddmm format (assuming 2025)
            day = int(date_str[:2])
            month = int(date_str[2:])
            date_obj = datetime(2025, month, day)
            dates_with_obj.append((date_str, date_obj))
        except:
            continue
    
    # Sort by date
    dates_with_obj.sort(key=lambda x: x[1])
    
    # Group into weeks (Friday to Thursday)
    weekly_groups = []
    current_week = []
    
    for date_str, date_obj in dates_with_obj:
        # If it's Friday (4) and we have a current week, start new week
        if date_obj.weekday() == 4 and current_week:  # Friday = 4
            weekly_groups.append(current_week)
            current_week = [date_str]
        else:
            current_week.append(date_str)
    
    # Add the last week if it exists
    if current_week:
        weekly_groups.append(current_week)
    
    return weekly_groups

def get_cpr_data(date_folder):
    """Get CPR values for the date"""
    try:
        utc_file = f"data/{date_folder}/tradeview_utc.csv"
        if os.path.exists(utc_file):
            df = pd.read_csv(utc_file)
            if not df.empty:
                daily_tc = df['Daily TC'].iloc[0]
                daily_bc = df['Daily BC'].iloc[0]
                daily_pivot = df['Daily Pivot'].iloc[0]
                
                # Get high and low for the day
                high = df['high'].max()
                low = df['low'].min()
                
                return {
                    'daily_tc': daily_tc,
                    'daily_bc': daily_bc,
                    'daily_pivot': daily_pivot,
                    'cpr_width': daily_tc - daily_bc,
                    'high': high,
                    'low': low
                }
    except Exception as e:
        print(f"Error reading CPR data for {date_folder}: {e}")
    
    return None

def get_trade_data(file_path):
    """Get trade statistics from a file with CORRECTED P/L % calculation"""
    if not os.path.exists(file_path):
        return {'count': 0, 'profitable': 0, 'total_pnl': 0.0, 'win_rate': 0.0, 'avg_pnl_pct': 0.0}
    
    try:
        df = pd.read_csv(file_path)
        if df.empty:
            return {'count': 0, 'profitable': 0, 'total_pnl': 0.0, 'win_rate': 0.0, 'avg_pnl_pct': 0.0}
        
        count = len(df)
        profitable = len(df[df['P/L'] > 0])
        total_pnl = df['P/L'].sum()
        win_rate = (profitable / count) * 100 if count > 0 else 0.0
        
        # CORRECTED P/L % calculation - sum all P/L % values (they are already percentages)
        if 'P/L %' in df.columns:
            try:
                # Convert P/L % to numeric, removing % sign
                pnl_pct_series = df['P/L %'].astype(str).str.replace('%', '')
                pnl_pct_numeric = pd.to_numeric(pnl_pct_series, errors='coerce')
                # Sum all P/L % values (don't divide by count - they're already percentages)
                total_pnl_pct = pnl_pct_numeric.sum()
                if pd.isna(total_pnl_pct):
                    total_pnl_pct = 0.0
                avg_pnl_pct = total_pnl_pct
            except:
                avg_pnl_pct = 0.0
        else:
            avg_pnl_pct = 0.0
        
        return {
            'count': count,
            'profitable': profitable,
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'avg_pnl_pct': avg_pnl_pct
        }
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return {'count': 0, 'profitable': 0, 'total_pnl': 0.0, 'win_rate': 0.0, 'avg_pnl_pct': 0.0}

def determine_trade_direction(cpr_data):
    """Determine trade direction based on CPR analysis"""
    if not cpr_data:
        return {
            'index_direction': 'Unknown',
            'reversal_call': False,
            'reversal_put': False,
            'continuation_call': False,
            'continuation_put': False
        }
    
    high = cpr_data['high']
    low = cpr_data['low']
    daily_tc = cpr_data['daily_tc']
    daily_bc = cpr_data['daily_bc']
    
    # Index Direction Logic
    if high > daily_tc and low > daily_bc:
        index_direction = "Call"  # Bullish day
    elif high < daily_tc and low < daily_bc:
        index_direction = "Put"   # Bearish day
    else:
        index_direction = "Mixed" # Mixed signals
    
    # Strategy Logic based on your requirements
    reversal_put = high < daily_tc      # Take PUT trades if high is below TC
    reversal_call = low > daily_bc      # Take CALL trades if low is above BC
    continuation_put = high < daily_tc   # Take PUT trades if high is below TC
    continuation_call = low > daily_bc   # Take CALL trades if low is above BC
    
    return {
        'index_direction': index_direction,
        'reversal_call': reversal_call,
        'reversal_put': reversal_put,
        'continuation_call': continuation_call,
        'continuation_put': continuation_put,
        'high': high,
        'low': low,
        'daily_tc': daily_tc,
        'daily_bc': daily_bc
    }

def get_index_trades_by_type(date_folder):
    """Get index trades separated by Call/Put from trades_crp folder"""
    try:
        file_path = f"data/{date_folder}/trades_crp/rev_v1_trades.csv"
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            if not df.empty:
                call_trades = df[df['Trade Type'].str.contains('Call', na=False)]
                put_trades = df[df['Trade Type'].str.contains('Put', na=False)]
                
                # Calculate P/L % for call trades - sum all P/L % values
                call_avg_pnl_pct = 0.0
                if len(call_trades) > 0 and 'P/L %' in call_trades.columns:
                    try:
                        call_pnl_pct = call_trades['P/L %'].astype(str).str.replace('%', '')
                        call_pnl_numeric = pd.to_numeric(call_pnl_pct, errors='coerce')
                        call_avg_pnl_pct = call_pnl_numeric.sum()
                        if pd.isna(call_avg_pnl_pct):
                            call_avg_pnl_pct = 0.0
                    except:
                        call_avg_pnl_pct = 0.0
                
                # Calculate P/L % for put trades - sum all P/L % values
                put_avg_pnl_pct = 0.0
                if len(put_trades) > 0 and 'P/L %' in put_trades.columns:
                    try:
                        put_pnl_pct = put_trades['P/L %'].astype(str).str.replace('%', '')
                        put_pnl_numeric = pd.to_numeric(put_pnl_pct, errors='coerce')
                        put_avg_pnl_pct = put_pnl_numeric.sum()
                        if pd.isna(put_avg_pnl_pct):
                            put_avg_pnl_pct = 0.0
                    except:
                        put_avg_pnl_pct = 0.0
                
                call_data = {
                    'count': len(call_trades),
                    'profitable': len(call_trades[call_trades['P/L'] > 0]),
                    'total_pnl': call_trades['P/L'].sum() if len(call_trades) > 0 else 0,
                    'win_rate': (len(call_trades[call_trades['P/L'] > 0]) / len(call_trades)) * 100 if len(call_trades) > 0 else 0,
                    'avg_pnl_pct': call_avg_pnl_pct
                }
                
                put_data = {
                    'count': len(put_trades),
                    'profitable': len(put_trades[put_trades['P/L'] > 0]),
                    'total_pnl': put_trades['P/L'].sum() if len(put_trades) > 0 else 0,
                    'win_rate': (len(put_trades[put_trades['P/L'] > 0]) / len(put_trades)) * 100 if len(put_trades) > 0 else 0,
                    'avg_pnl_pct': put_avg_pnl_pct
                }
                
                return call_data, put_data
    except Exception as e:
        print(f"Error processing index trades for {date_folder}: {e}")
    
    return {'count': 0, 'profitable': 0, 'total_pnl': 0.0, 'win_rate': 0.0, 'avg_pnl_pct': 0.0}, {'count': 0, 'profitable': 0, 'total_pnl': 0.0, 'win_rate': 0.0, 'avg_pnl_pct': 0.0}

def format_trade_data(data, should_trade):
    """Format trade data for display"""
    if not should_trade:
        return "❌ No Signal"
    if data['count'] == 0:
        return "0 / 0% / ₹0.00 / 0.0%"
    
    # Safety check for avg_pnl_pct
    avg_pnl_pct = data.get('avg_pnl_pct', 0.0)
    return f"{data['count']} / {data['win_rate']:.1f}% / ₹{data['total_pnl']:.2f} / {avg_pnl_pct:.1f}%"

def calculate_row_total(strategy_data_list):
    """Calculate total for a single row (aggregate of all strategies for one date)"""
    total_count = 0
    total_profitable = 0
    total_pnl = 0.0
    total_pnl_pct = 0.0
    
    for data, should_trade in strategy_data_list:
        if should_trade and data['count'] > 0:
            total_count += data['count']
            total_profitable += data['profitable']
            total_pnl += data['total_pnl']
            # Sum the P/L percentages (they are already percentages)
            avg_pnl_pct = data.get('avg_pnl_pct', 0.0)
            total_pnl_pct += avg_pnl_pct
    
    return {
        'count': total_count,
        'profitable': total_profitable,
        'total_pnl': total_pnl,
        'win_rate': (total_profitable / total_count) * 100 if total_count > 0 else 0.0,
        'avg_pnl_pct': total_pnl_pct
    }

def build_analytics_report_for_date(date_folder):
    """Build comprehensive analytics report for a single date"""
    # Get CPR data
    cpr_data = get_cpr_data(date_folder)
    if not cpr_data:
        return None
    
    # Determine trade directions
    trade_logic = determine_trade_direction(cpr_data)
    
    # Get trade data for all strategies
    base_path = f"data/{date_folder}"
    
    # Index trades (from trades_crp folder)
    index_call_data, index_put_data = get_index_trades_by_type(date_folder)
    
    # Reversal trades
    reversal_call_data = get_trade_data(f"{base_path}/call/trades/call_rev_v2_trades.csv")
    reversal_put_data = get_trade_data(f"{base_path}/put/trades/put_rev_v2_trades.csv")
    
    # Calculate row total (aggregate of all active strategies)
    row_total_data = calculate_row_total([
        (index_call_data, trade_logic['index_direction'] in ['Call', 'Mixed']),
        (index_put_data, trade_logic['index_direction'] in ['Put', 'Mixed']),
        (reversal_call_data, trade_logic['reversal_call']),
        (reversal_put_data, trade_logic['reversal_put'])
    ])
    
    # Create summary row
    summary_row = {
        'Date': date_folder,
        'CPR_Width': f"{cpr_data['cpr_width']:.2f}",
        'Index_Call': format_trade_data(index_call_data, trade_logic['index_direction'] in ['Call', 'Mixed']),
        'Index_Put': format_trade_data(index_put_data, trade_logic['index_direction'] in ['Put', 'Mixed']),
        'Reversal_Call': format_trade_data(reversal_call_data, trade_logic['reversal_call']),
        'Reversal_Put': format_trade_data(reversal_put_data, trade_logic['reversal_put']),
        'Total': format_trade_data(row_total_data, True)
    }
    
    return summary_row

def run_analysis():
    """Build consolidated report grouped by weeks"""
    print(f"\n{'='*120}")
    print(f"BUILDING WEEKLY CPR-BASED ANALYTICS REPORT")
    print(f"{'='*120}")
    
    # Get all date directories
    data_dirs = glob.glob("data/*/")
    date_folders = [d.split('/')[1] for d in data_dirs if len(d.split('/')[1]) == 4]  # ddmm format
    date_folders.sort()
    
    print(f"Found {len(date_folders)} date directories: {date_folders}")
    
    # Group dates into weeks
    weekly_groups = get_weekly_groups(date_folders)
    
    all_summaries = []
    
    # Process each week
    for week_num, week_dates in enumerate(weekly_groups, 1):
        print(f"\n{'='*80}")
        print(f"WEEK {week_num}: {week_dates[0]} to {week_dates[-1]}")
        print(f"{'='*80}")
        
        week_summaries = []
        
        # Process each date in the week
        for date_folder in week_dates:
            summary = build_analytics_report_for_date(date_folder)
            if summary:
                # Only include rows that have some activity (exclude zero totals)
                if summary['Total'] != "0 / 0% / ₹0.00 / 0.0%":
                    week_summaries.append(summary)
                    all_summaries.append(summary)
                    print(f"✅ {date_folder}: {summary['Total']}")
                else:
                    print(f"⚪ {date_folder}: No activity (excluded)")
        
        if week_summaries:
            print(f"\n📊 WEEK {week_num} SUMMARY:")
            print(f"| {'Date':<6} | {'CPR Width':<10} | {'Index Call':<30} | {'Index Put':<30} | {'Reversal Call':<30} | {'Reversal Put':<30} | {'Total':<30} |")
            print(f"|{'-'*8}|{'-'*12}|{'-'*32}|{'-'*32}|{'-'*32}|{'-'*32}|{'-'*32}|")
            
            for summary in week_summaries:
                print(f"| {summary['Date']:<6} | {summary['CPR_Width']:<10} | {summary['Index_Call']:<30} | {summary['Index_Put']:<30} | {summary['Reversal_Call']:<30} | {summary['Reversal_Put']:<30} | {summary['Total']:<30} |")
            
            # Calculate and display week totals
            week_totals = calculate_totals(week_summaries)
            print(f"|{'-'*8}|{'-'*12}|{'-'*32}|{'-'*32}|{'-'*32}|{'-'*32}|{'-'*32}|")
            print(f"| {'TOTAL':<6} | {'':<10} | {week_totals['Index_Call']:<30} | {week_totals['Index_Put']:<30} | {week_totals['Reversal_Call']:<30} | {week_totals['Reversal_Put']:<30} | {week_totals['Total']:<30} |")
    
    # Create final consolidated table (excluding zero rows)
    if all_summaries:
        print(f"\n{'='*120}")
        print(f"FINAL CONSOLIDATED ANALYTICS SUMMARY - ALL ACTIVE DATES")
        print(f"{'='*120}")
        print("Note: Dates with zero activity have been excluded")
        
        # Print table header
        print(f"| {'Date':<6} | {'CPR Width':<10} | {'Index Call':<30} | {'Index Put':<30} | {'Reversal Call':<30} | {'Reversal Put':<30} | {'Total':<30} |")
        print(f"|{'-'*8}|{'-'*12}|{'-'*32}|{'-'*32}|{'-'*32}|{'-'*32}|{'-'*32}|")
        
        # Print each row
        for summary in all_summaries:
            print(f"| {summary['Date']:<6} | {summary['CPR_Width']:<10} | {summary['Index_Call']:<30} | {summary['Index_Put']:<30} | {summary['Reversal_Call']:<30} | {summary['Reversal_Put']:<30} | {summary['Total']:<30} |")
        
        # Calculate totals
        totals = calculate_totals(all_summaries)
        
        # Print totals row
        print(f"|{'-'*8}|{'-'*12}|{'-'*32}|{'-'*32}|{'-'*32}|{'-'*32}|{'-'*32}|")
        print(f"| {'TOTAL':<6} | {'':<10} | {totals['Index_Call']:<30} | {totals['Index_Put']:<30} | {totals['Reversal_Call']:<30} | {totals['Reversal_Put']:<30} | {totals['Total']:<30} |")
        
        # Build comprehensive weekly report content
        weekly_content = "--- Weekly CPR-Based Analytics Report ---\n\n"
        weekly_content += "Format: Trades / Win% / ₹P&L / P/L%\n"
        weekly_content += "Note: Dates with zero activity have been excluded\n\n"
        
        # Add each week's data
        for week_num, week_dates in enumerate(weekly_groups, 1):
            week_summaries_for_file = []
            for date_folder in week_dates:
                summary = build_analytics_report_for_date(date_folder)
                if summary and summary['Total'] != "0 / 0% / ₹0.00 / 0.0%":
                    week_summaries_for_file.append(summary)
            
            if week_summaries_for_file:
                weekly_content += f"=== WEEK {week_num}: {week_dates[0]} to {week_dates[-1]} ===\n\n"
                weekly_content += f"| {'Date':<6} | {'CPR Width':<10} | {'Index Call':<30} | {'Index Put':<30} | {'Reversal Call':<30} | {'Reversal Put':<30} | {'Total':<30} |\n"
                weekly_content += f"|{'-'*8}|{'-'*12}|{'-'*32}|{'-'*32}|{'-'*32}|{'-'*32}|{'-'*32}|\n"
                
                for summary in week_summaries_for_file:
                    weekly_content += f"| {summary['Date']:<6} | {summary['CPR_Width']:<10} | {summary['Index_Call']:<30} | {summary['Index_Put']:<30} | {summary['Reversal_Call']:<30} | {summary['Reversal_Put']:<30} | {summary['Total']:<30} |\n"
                
                # Add week totals
                week_totals = calculate_totals(week_summaries_for_file)
                weekly_content += f"|{'-'*8}|{'-'*12}|{'-'*32}|{'-'*32}|{'-'*32}|{'-'*32}|{'-'*32}|\n"
                weekly_content += f"| {'TOTAL':<6} | {'':<10} | {week_totals['Index_Call']:<30} | {week_totals['Index_Put']:<30} | {week_totals['Reversal_Call']:<30} | {week_totals['Reversal_Put']:<30} | {week_totals['Total']:<30} |\n\n"
        
        # Add final consolidated summary
        weekly_content += "=== FINAL CONSOLIDATED SUMMARY - ALL ACTIVE DATES ===\n\n"
        weekly_content += f"| {'Date':<6} | {'CPR Width':<10} | {'Index Call':<30} | {'Index Put':<30} | {'Reversal Call':<30} | {'Reversal Put':<30} | {'Total':<30} |\n"
        weekly_content += f"|{'-'*8}|{'-'*12}|{'-'*32}|{'-'*32}|{'-'*32}|{'-'*32}|{'-'*32}|\n"
        
        for summary in all_summaries:
            weekly_content += f"| {summary['Date']:<6} | {summary['CPR_Width']:<10} | {summary['Index_Call']:<30} | {summary['Index_Put']:<30} | {summary['Reversal_Call']:<30} | {summary['Reversal_Put']:<30} | {summary['Total']:<30} |\n"
        
        # Add overall totals
        weekly_content += f"|{'-'*8}|{'-'*12}|{'-'*32}|{'-'*32}|{'-'*32}|{'-'*32}|{'-'*32}|\n"
        weekly_content += f"| {'TOTAL':<6} | {'':<10} | {totals['Index_Call']:<30} | {totals['Index_Put']:<30} | {totals['Reversal_Call']:<30} | {totals['Reversal_Put']:<30} | {totals['Total']:<30} |\n"
        
        try:
            with open("final_analytics_report.txt", 'w') as f:
                f.write(weekly_content)
            print(f"\n💾 Comprehensive weekly report saved to: final_analytics_report.txt")

            # Generate PDF report
            generate_pdf_report(weekly_content, "final_analytics_report.pdf")
            print(f"💾 Comprehensive weekly report saved to: final_analytics_report.pdf")
        except Exception as e:
            print(f"❌ Error saving weekly report: {e}")

def calculate_totals(all_summaries):
    """Calculate totals across all dates for each strategy"""
    totals = {
        'Index_Call': {'count': 0, 'profitable': 0, 'total_pnl': 0.0, 'weighted_pnl_pct': 0.0},
        'Index_Put': {'count': 0, 'profitable': 0, 'total_pnl': 0.0, 'weighted_pnl_pct': 0.0},
        'Reversal_Call': {'count': 0, 'profitable': 0, 'total_pnl': 0.0, 'weighted_pnl_pct': 0.0},
        'Reversal_Put': {'count': 0, 'profitable': 0, 'total_pnl': 0.0, 'weighted_pnl_pct': 0.0},
        'Total': {'count': 0, 'profitable': 0, 'total_pnl': 0.0, 'weighted_pnl_pct': 0.0}
    }
    
    # Parse each summary and accumulate totals
    for summary in all_summaries:
        for strategy in ['Index_Call', 'Index_Put', 'Reversal_Call', 'Reversal_Put', 'Total']:
            data = parse_trade_data_from_string(summary[strategy])
            totals[strategy]['count'] += data['count']
            totals[strategy]['profitable'] += data['profitable']
            totals[strategy]['total_pnl'] += data['total_pnl']
            # Sum the P/L percentages (they are already percentages, not weighted averages)
            totals[strategy]['weighted_pnl_pct'] += data['avg_pnl_pct']
    
    # Format totals for display
    formatted_totals = {}
    for strategy, data in totals.items():
        if data['count'] == 0:
            formatted_totals[strategy] = "0 / 0% / ₹0.00 / 0.0%"
        else:
            win_rate = (data['profitable'] / data['count']) * 100
            total_pnl_pct = data['weighted_pnl_pct']  # This is now the sum of all P/L %
            formatted_totals[strategy] = f"{data['count']} / {win_rate:.1f}% / ₹{data['total_pnl']:.2f} / {total_pnl_pct:.1f}%"
    
    return formatted_totals

def generate_pdf_report(content, filename):
    """Generate a properly formatted PDF report with tables optimized for A4 size"""
    try:
        # Create document with A4 page size and proper margins
        doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Create custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=14,
            spaceAfter=12,
            alignment=1,  # Center alignment
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=11,
            spaceAfter=8,
            spaceBefore=12,
            textColor=colors.darkgreen
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=9,
            spaceAfter=6
        )
        
        # Story to hold all content
        story = []
        
        # Parse content and create formatted elements
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
            
            # Handle main title
            if line.startswith('--- Weekly CPR-Based Analytics Report ---'):
                story.append(Paragraph(line.replace('---', '').strip(), title_style))
                i += 1
                continue
            
            # Handle section headers
            if line.startswith('===') and line.endswith('==='):
                section_title = line.replace('=', '').strip()
                story.append(Paragraph(section_title, heading_style))
                i += 1
                continue
            
            # Handle format description and notes
            if line.startswith('Format:') or line.startswith('Note:'):
                story.append(Paragraph(line, normal_style))
                i += 1
                continue
            
            # Handle table headers and data
            if line.startswith('|') and 'Date' in line:
                # Found a table - collect all table rows
                table_data = []
                
                # Process table header
                header_row = [cell.strip() for cell in line.split('|')[1:-1]]  # Remove empty first/last elements
                table_data.append(header_row)
                i += 1
                
                # Skip separator line
                if i < len(lines) and lines[i].strip().startswith('|---'):
                    i += 1
                
                # Collect all data rows including TOTAL rows
                while i < len(lines):
                    current_line = lines[i].strip()
                    if current_line.startswith('|') and not current_line.startswith('|---'):
                        if 'Date' not in current_line:  # Skip if it's another header
                            data_row = [cell.strip() for cell in current_line.split('|')[1:-1]]
                            # Handle currency symbol replacement
                            data_row = [cell.replace('₹', 'Rs.').replace('❌', 'X') for cell in data_row]
                            table_data.append(data_row)
                        i += 1
                    elif current_line.startswith('|---'):
                        i += 1  # Skip separator lines
                    else:
                        break
                
                # Create and style the table
                if table_data and len(table_data) > 1:  # Ensure we have data beyond header
                    # Calculate column widths for A4 page (7.2 inches available width)
                    col_widths = [
                        0.4 * inch,   # Date - smaller
                        0.6 * inch,   # CPR Width - smaller  
                        1.1 * inch,   # Index Call
                        1.1 * inch,   # Index Put
                        1.1 * inch,   # Reversal Call
                        1.1 * inch,   # Reversal Put
                        1.3 * inch    # Total - larger to prevent spillover
                    ]
                    
                    table = Table(table_data, colWidths=col_widths, repeatRows=1)
                    
                    # Build table styling dynamically
                    table_style = [
                        # Header styling
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.darkblue),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 6),
                        
                        # Data styling
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 4),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('WORDWRAP', (0, 0), (-1, -1), True),
                        
                        # Padding
                        ('TOPPADDING', (0, 0), (-1, -1), 1),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                        ('LEFTPADDING', (0, 0), (-1, -1), 1),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
                    ]
                    
                    # Apply alternating colors and identify TOTAL rows
                    for row_idx in range(1, len(table_data)):
                        row_data = table_data[row_idx]
                        if len(row_data) > 0 and row_data[0] == 'TOTAL':  # TOTAL row
                            table_style.extend([
                                ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightyellow),
                                ('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'),
                                ('FONTSIZE', (0, row_idx), (-1, row_idx), 4),
                            ])
                        else:  # Regular data row
                            bg_color = colors.white if row_idx % 2 == 1 else colors.lightgrey
                            table_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), bg_color))
                    
                    table.setStyle(TableStyle(table_style))
                    
                    story.append(table)
                    story.append(Spacer(1, 8))
                continue
            
            # Handle other text
            if line:
                story.append(Paragraph(line, normal_style))
            
            i += 1
        
        # Build PDF
        doc.build(story)
        print(f"✅ PDF report generated successfully: {filename}")
        
    except Exception as e:
        print(f"❌ Error generating PDF report: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback to simple text-based PDF if table approach fails
        try:
            print("🔄 Attempting fallback PDF generation...")
            generate_simple_pdf_fallback(content, filename)
        except Exception as fallback_error:
            print(f"❌ Fallback PDF generation also failed: {fallback_error}")

def generate_simple_pdf_fallback(content, filename):
    """Fallback PDF generation with better formatting than original"""
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    
    # Set font and size
    c.setFont("Courier", 7)
    
    # Calculate margins and line height
    margin = 40
    line_height = 10
    max_lines_per_page = int((height - 2 * margin) / line_height)
    
    lines = content.split('\n')
    current_line = 0
    page_line_count = 0
    
    # Start text object
    text_object = c.beginText(margin, height - margin)
    
    for line in lines:
        # Handle long lines by wrapping them
        if len(line) > 100:  # If line is too long
            wrapped_lines = []
            while len(line) > 100:
                # Find a good break point (space or |)
                break_point = 100
                for i in range(99, 80, -1):
                    if line[i] in [' ', '|']:
                        break_point = i
                        break
                
                wrapped_lines.append(line[:break_point])
                line = line[break_point:].lstrip()
            
            if line:  # Add remaining part
                wrapped_lines.append(line)
            
            # Add wrapped lines
            for wrapped_line in wrapped_lines:
                if page_line_count >= max_lines_per_page - 2:
                    c.drawText(text_object)
                    c.showPage()
                    c.setFont("Courier", 7)
                    text_object = c.beginText(margin, height - margin)
                    page_line_count = 0
                
                text_object.textLine(wrapped_line)
                page_line_count += 1
        else:
            # Regular line
            if page_line_count >= max_lines_per_page - 2:
                c.drawText(text_object)
                c.showPage()
                c.setFont("Courier", 7)
                text_object = c.beginText(margin, height - margin)
                page_line_count = 0
            
            text_object.textLine(line)
            page_line_count += 1
    
    # Draw final text and save
    c.drawText(text_object)
    c.save()
    print(f"✅ Fallback PDF report generated: {filename}")

def parse_trade_data_from_string(trade_string):
    """Parse trade data from formatted string back to numbers"""
    if trade_string == "❌ No Signal" or trade_string.startswith("0 / 0%"):
        return {'count': 0, 'profitable': 0, 'total_pnl': 0.0, 'avg_pnl_pct': 0.0}
    
    try:
        # Parse format: "count / win_rate% / ₹total_pnl / avg_pnl_pct%" or older format without P/L%
        parts = trade_string.split(' / ')
        count = int(parts[0])
        win_rate = float(parts[1].replace('%', ''))
        total_pnl = float(parts[2].replace('₹', ''))
        avg_pnl_pct = float(parts[3].replace('%', '')) if len(parts) > 3 else 0.0
        profitable = int((count * win_rate) / 100)
        
        return {
            'count': count,
            'profitable': profitable,
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'avg_pnl_pct': avg_pnl_pct
        }
    except:
        return {'count': 0, 'profitable': 0, 'total_pnl': 0.0, 'avg_pnl_pct': 0.0}

if __name__ == "__main__":
    run_analysis()
