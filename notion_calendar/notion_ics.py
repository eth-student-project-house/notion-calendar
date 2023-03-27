from datetime import datetime, timezone
from icalendar import Calendar, Event
from notion_client import Client
from notion_client.helpers import collect_paginated_api
from collections import OrderedDict
from flask import current_app

def extract_rich_text(rich_text_field):
    return ''.join([val['plain_text'] for val in rich_text_field.get('rich_text', [])])

def get_ical(notion, db_id, title_format):
    # Fetch database
    # Pagination: https://developers.notion.com/reference/intro#pagination
    # Querying DB: https://developers.notion.com/reference/post-database-query
    calendar_entries = collect_paginated_api(notion.databases.query,
        database_id=db_id,
        filter={'property': 'Date', 'date': {'after': '2023-01-01'}},
        sorts=[{'property': 'Date', 'direction': 'descending'}])
    cal = Calendar()
    cal.add("summary", "Imported from Notion, via notion-export-ics.")
    cal.add('version', '2.0')
    cal.add('prodid', 'https://github.com/eth-student-project-house/notion-calendar')
    cal.add('name', 'SPH Notion Events')

    # Print props
    # event_props = calendar_entries[52]      
    # current_app.logger.info(event_props)

    for notion_event in calendar_entries:
        event_props = notion_event["properties"]
        url = notion_event["url"]

        # Skip events without title or date
        title = ''.join([val['plain_text'] for val in event_props.get('Name', {}).get('title', [])])
        if title == '' or event_props.get('Date') is None:
            current_app.logger.warning('Skipping (no title or date): ' + url)
            continue

        # Put in ICS file
        event = Event()

        # Name (title)
        if title == 'Event-Template':
            continue
        event.add('summary', title)

        # Date
        def to_datetime(date_str):
            # Only date is provided, no time.
            if len(date_str) == 10:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # We give times in UTC, otherwise it's a mess.
            return datetime.fromisoformat(date_str).astimezone(timezone.utc)

        date = event_props['Date']['date']
        event.add('dtstart', to_datetime(date['start']))
        if date.get('end') is not None:
            event.add('dtend', to_datetime(date['end']))
            
        # Location
        if event_props.get('Location') is not None:
            locations = ', '.join([val['name'] for val in event_props['Location']['multi_select']])
            event.add('location', locations)
        
        ### Description ###
        # URL
        desc = ''
        desc += f'Notion URL: {url}\n'

        # Number of participants
        num_of_participants = event_props.get('Number of participants (Capacity)', {}).get('number', '')
        desc += f'Number of participants (Capacity): {num_of_participants}\n'

        # Applicant org, Applicant name and Set up Timeframe
        rich_text_props = ['Applicant organisation', 'Applicant name', 'Set up Timeframe']
        for prop_name in rich_text_props:
            value = extract_rich_text(event_props.get(prop_name, {}))
            desc += f'{prop_name}: {value}\n'

        event.add('description', desc)


        # UID (required)
        event.add('uid', notion_event["id"])
        
        # DTSTAMP (required)
        # https://stackoverflow.com/a/67712346 + ChatGPT magic
        event.add('dtstamp', datetime.fromisoformat(notion_event["created_time"].replace('Z', '+00:00')))
        
        cal.add_component(event)

    return cal
