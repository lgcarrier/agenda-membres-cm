import os
import csv
import html
import json
from datetime import datetime, timedelta
from pathlib import Path

def parse_date(date_str):
    """Parse date from DD-MM-YYYY format"""
    return datetime.strptime(date_str, "%d-%m-%Y")

def parse_time(time_str):
    """Parse time from HHhMM format"""
    if not time_str:
        return None
    return datetime.strptime(time_str, "%Hh%M").time()

def get_minister_name(filename):
    """Extract minister name from filename"""
    base = os.path.basename(filename)
    name = os.path.splitext(base)[0]
    return name.replace('-', ' ').title()

def read_agenda_file(filepath):
    """Read and parse a CSV agenda file"""
    activities = []
    # Determine if minister is active based on file path
    status = "active" if "/active/" in str(filepath) else "inactive"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';', quotechar='"')
        next(reader)  # Skip header
        for row in reader:
            if len(row) >= 5:  # Ensure we have enough columns
                activity_type = html.unescape(row[0])
                description = html.unescape(row[1].replace('<p>', '').replace('</p>', '').strip())
                location = html.unescape(row[2])
                date_str = row[3]
                time_str = row[4]
                participants = html.unescape(row[5]) if len(row) > 5 else ""

                try:
                    date = parse_date(date_str)
                    time = parse_time(time_str) if time_str else None
                    activities.append({
                        'type': activity_type,
                        'description': description,
                        'location': location,
                        'date': date,
                        'time': time,
                        'participants': participants,
                        'minister': get_minister_name(filepath),
                        'minister_status': status
                    })
                except ValueError:
                    continue  # Skip invalid dates/times
    return activities

def generate_daily_summary_markdown(activities, date):
    """Generate markdown content for a specific day"""
    day_activities = [a for a in activities if a['date'].date() == date.date()]
    if not day_activities:
        return None
    
    content = [f"# Agenda des ministres - {date.strftime('%d %B %Y')}\n"]
    
    # Sort activities by time, placing those without a time at the end
    day_activities.sort(key=lambda x: (x['time'] is None, x['time']))
    
    for activity in day_activities:
        time_str = activity['time'].strftime('%H:%M') if activity['time'] else 'Heure non spécifiée'
        minister = activity['minister']
        desc = activity['description'] or activity['type']
        loc = activity['location']
        
        content.append(f"## {time_str} - {minister}")
        content.append(f"**{desc}**")
        content.append(f"*Lieu: {loc}*")
        
        if activity['participants']:
            content.append("\nParticipants:")
            content.append(activity['participants'])
        
        content.append("\n---\n")
    
    return '\n'.join(content)

def generate_daily_summary_json(activities, date):
    """Generate JSON data for a specific day"""
    day_activities = [a for a in activities if a['date'].date() == date.date()]
    if not day_activities:
        return None
    
    day_activities.sort(key=lambda x: (x['time'] is None, x['time']))
    
    events = []
    for activity in day_activities:
        events.append({
            'time': activity['time'].strftime('%H:%M') if activity['time'] else 'Heure non spécifiée',
            'minister': activity['minister'],
            'minister_status': activity['minister_status'],
            'description': activity['description'] or activity['type'],
            'location': activity['location'],
            'participants': activity['participants']
        })
    
    return {'date': date.strftime('%Y-%m-%d'), 'events': events}

def generate_weekly_summary(daily_summaries):
    """Aggregate a list of daily summaries into a weekly summary JSON"""
    week_data = [summary for summary in daily_summaries if summary is not None]
    return {'week': week_data}

def main():
    # Create output directory for daily summaries if it doesn't exist
    output_dir = Path('daily_summaries')
    output_dir.mkdir(exist_ok=True)
    
    # Read all agendas (active and inactive)
    all_activities = []
    
    # Read active agendas
    active_dir = Path('minister_agendas/active')
    for csv_file in active_dir.glob('*.csv'):
        activities = read_agenda_file(csv_file)
        all_activities.extend(activities)
    
    # Read inactive agendas
    inactive_dir = Path('minister_agendas/inactive')
    for csv_file in inactive_dir.glob('*.csv'):
        activities = read_agenda_file(csv_file)
        all_activities.extend(activities)
    
    all_daily_json = []
    today = datetime.now()
    
    # Generate summaries for the last 31 days
    for i in range(31):
        date = today - timedelta(days=i)
        
        # Markdown summary
        markdown_summary = generate_daily_summary_markdown(all_activities, date)
        if markdown_summary:
            md_output_file = output_dir / f"{date.strftime('%Y-%m-%d')}.md"
            with open(md_output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_summary)
        
        # JSON summary
        daily_json = generate_daily_summary_json(all_activities, date)
        if daily_json:
            json_output_file = output_dir / f"{date.strftime('%Y-%m-%d')}.json"
            with open(json_output_file, 'w', encoding='utf-8') as f:
                json.dump(daily_json, f, ensure_ascii=False, indent=2)
            all_daily_json.append(daily_json)
    
    # Generate weekly summary JSON file
    weekly_summary = generate_weekly_summary(all_daily_json)
    with open("weekly_summary.json", 'w', encoding='utf-8') as f:
        json.dump(weekly_summary, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()
