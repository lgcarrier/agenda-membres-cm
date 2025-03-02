import os
import csv
import html
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
                        'minister': get_minister_name(filepath)
                    })
                except ValueError:
                    continue  # Skip invalid dates/times
    return activities

def generate_daily_summary(activities, date):
    """Generate markdown content for a specific day"""
    day_activities = [a for a in activities if a['date'].date() == date.date()]
    if not day_activities:
        return None
    
    content = [f"# Agenda des ministres - {date.strftime('%d %B %Y')}\n"]
    
    # Sort activities by time, putting activities without time at the end
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

def main():
    # Create output directory
    output_dir = Path('daily_summaries')
    output_dir.mkdir(exist_ok=True)
    
    # Read all active agendas
    all_activities = []
    active_dir = Path('minister_agendas/active')
    for csv_file in active_dir.glob('*.csv'):
        activities = read_agenda_file(csv_file)
        all_activities.extend(activities)
    
    # Generate summaries for the last 7 days
    today = datetime.now()
    for i in range(7):
        date = today - timedelta(days=i)
        summary = generate_daily_summary(all_activities, date)
        if summary:
            output_file = output_dir / f"{date.strftime('%Y-%m-%d')}.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(summary)

if __name__ == '__main__':
    main()