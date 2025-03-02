#!/usr/bin/env python3
import csv
import os
from datetime import datetime, timedelta
from icalendar import Calendar, Event, vDate, vDatetime
import html
import logging
import pytz

# Set up timezone for Quebec
TIMEZONE = pytz.timezone('America/Montreal')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('minister_agendas.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def clean_html(text):
    """Remove HTML tags and decode HTML entities"""
    if not text:
        return ""
    
    # First decode HTML entities
    text = html.unescape(text)
    
    # Remove HTML tags while preserving line breaks
    text = text.replace('<p>', '').replace('</p>', '\n')
    text = text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
    text = text.replace('<sup>', '').replace('</sup>', '')
    text = text.replace('<strong>', '').replace('</strong>', '')
    
    # Remove any remaining HTML tags (if any)
    import re
    text = re.sub(r'<[^>]+>', '', text)
    
    # Clean up multiple newlines and whitespace
    text = re.sub(r'\n\s*\n', '\n', text)
    text = text.strip()
    
    return text

def parse_datetime(date_str, time_str):
    """Parse date and time strings into datetime object"""
    if not date_str:
        return None
    
    try:
        # Extract just the date part and validate it matches DD-MM-YYYY pattern
        import re
        date_match = re.match(r'(\d{2}-\d{2}-\d{4})', date_str)
        if not date_match:
            return None
            
        date_str = date_match.group(1)
        date_obj = datetime.strptime(date_str, '%d-%m-%Y')
        
        # If time is provided, combine with date
        if time_str:
            # Remove 'h' and parse time
            time_str = time_str.replace('h', ':')
            if ':' not in time_str:
                time_str += ':00'
            # Validate time format
            if not re.match(r'^\d{1,2}:\d{2}$', time_str):
                return date_obj
            time_obj = datetime.strptime(time_str, '%H:%M')
            return datetime.combine(date_obj.date(), time_obj.time())
        
        return date_obj
    except ValueError as e:
        logger.warning(f"Error parsing date/time: {date_str} {time_str} - {str(e)}")
        return None

def parse_csv_content(content):
    """Parse CSV content handling multi-line entries and HTML content"""
    rows = []
    current_row = None
    headers = None
    
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # Count quotes to detect if this is a continuation line
        quote_count = line.count('"')
        has_semicolon = ';' in line
        
        # If this looks like a header or complete row
        if quote_count >= 2 and has_semicolon:
            # Process previous row if exists
            if current_row is not None:
                rows.append(current_row)
            
            # Split fields handling quoted values
            fields = []
            current_field = ''
            in_quotes = False
            
            for char in line:
                if char == '"':
                    in_quotes = not in_quotes
                elif char == ';' and not in_quotes:
                    fields.append(clean_html(current_field.strip(' "')))
                    current_field = ''
                else:
                    current_field += char
            
            if current_field:
                fields.append(clean_html(current_field.strip(' "')))
            
            # Handle header row
            if headers is None:
                headers = fields
                continue
                
            # Handle rows that might have missing trailing fields
            while len(fields) < len(headers):
                fields.append("")
                
            # Create new row dict
            current_row = dict(zip(headers, fields))
        else:
            # This is a continuation of the previous row (probably participants)
            if current_row is not None:
                # Add this line to the participants field
                current_content = current_row.get('Participants', '').strip()
                if current_content:
                    current_row['Participants'] = current_content + '\n' + clean_html(line.strip(' "'))
                else:
                    current_row['Participants'] = clean_html(line.strip(' "'))
    
    # Add the last row if exists
    if current_row is not None:
        rows.append(current_row)
        
    return headers, rows

def convert_csv_to_ical(csv_path, ical_path):
    """Convert a CSV file to iCal format"""
    cal = Calendar()
    cal.add('prodid', '-//Agenda Membres CM//FR')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('x-wr-timezone', 'America/Montreal')

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
            headers, rows = parse_csv_content(content)
            
            events_added = False
            for row in rows:
                event = Event()
                
                # Clean and prepare event data
                activity_type = row.get("Type d'activité", "").strip()
                description = row.get('Description', "").strip()
                location = row.get('Lieu', "").strip()
                date = row.get('Date', "").strip()
                time = row.get('Heure', "").strip()
                participants = row.get('Participants', "").strip()

                # Skip if no date
                if not date:
                    continue

                # Create event summary
                summary = description if description else activity_type
                if not summary:
                    continue

                # Parse start datetime
                start_dt = parse_datetime(date, time)
                if not start_dt:
                    continue

                # Add event details
                event.add('summary', summary)
                
                # Handle all-day vs timed events
                if time:
                    # For timed events, add timezone
                    start_dt = TIMEZONE.localize(start_dt)
                    event['dtstart'] = start_dt
                    # Set duration to 1 hour
                    event.add('duration', timedelta(hours=1))
                else:
                    # For all-day events, use date
                    event['dtstart'] = start_dt.date()
                
                if location:
                    event.add('location', location)
                
                # Combine all details for description
                full_description = []
                if activity_type:
                    full_description.append(f"Type: {activity_type}")
                if description:
                    full_description.append(f"Description: {description}")
                if participants:
                    # Split participants by newlines and clean each line
                    participant_lines = [line.strip() for line in participants.split('\n') if line.strip()]
                    if participant_lines:
                        full_description.append("Participants:")
                        full_description.extend(f"- {p}" for p in participant_lines)
                
                event.add('description', '\n'.join(full_description))
                cal.add_component(event)
                events_added = True

            if events_added:  # Only write file if we have events
                # Write the iCal file
                with open(ical_path, 'wb') as f:
                    f.write(cal.to_ical())
                logger.info(f"Successfully created iCal file: {ical_path}")
                return True
            else:
                logger.warning(f"No valid events found in {csv_path}")
                return False

    except Exception as e:
        logger.error(f"Error processing {csv_path}: {str(e)}")
        return False

def main():
    base_dir = 'minister_agendas'
    
    # Process active ministers
    active_dir = os.path.join(base_dir, 'active')
    active_ical_dir = os.path.join(base_dir, 'active_ical')
    
    # Process inactive ministers
    inactive_dir = os.path.join(base_dir, 'inactive')
    inactive_ical_dir = os.path.join(base_dir, 'inactive_ical')
    
    # Ensure output directories exist
    os.makedirs(active_ical_dir, exist_ok=True)
    os.makedirs(inactive_ical_dir, exist_ok=True)
    
    # Process active ministers
    for csv_file in os.listdir(active_dir):
        if csv_file.endswith('.csv'):
            csv_path = os.path.join(active_dir, csv_file)
            ical_path = os.path.join(active_ical_dir, csv_file.replace('.csv', '.ics'))
            convert_csv_to_ical(csv_path, ical_path)
    
    # Process inactive ministers
    for csv_file in os.listdir(inactive_dir):
        if csv_file.endswith('.csv'):
            csv_path = os.path.join(inactive_dir, csv_file)
            ical_path = os.path.join(inactive_ical_dir, csv_file.replace('.csv', '.ics'))
            convert_csv_to_ical(csv_path, ical_path)

if __name__ == "__main__":
    main()