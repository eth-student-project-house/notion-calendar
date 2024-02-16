from datetime import datetime, timezone, timedelta
import icalendar
from notion_client import Client
from notion_client.helpers import collect_paginated_api
from collections import OrderedDict
from flask import current_app

from typing import Callable, Any

COLOR_TO_GERMAN = {
    'Blue': 'Blaue',
    'Yellow': 'Gelbe',
    'Green': 'Grüne',
    'Orange': 'Orangefarbene',
    'Red': 'Rote',
    'Purple': 'Lila'
}

P_APPLICANT_ORGANISATION = 'Applicant organisation'
P_APPLICANT_NAME = 'Applicant name'
P_SET_UP_TIMEFRAME = 'Set up Timeframe'

EXLUCDE_TAG_OUTLOOK = 'Exclude from Outlook Calendar'
EXLUCDE_TAG_ENTRANCE_SCREEN = 'Exclude from Entrance Screen'

REQUEST_STATUS_DONE = 'Done'

EVENT_TYPE_TOUR = 'Tour'

def fetch_events(notion, db_id):
    # Fetch database
    # Pagination: https://developers.notion.com/reference/intro#pagination
    # Querying DB: https://developers.notion.com/reference/post-database-query
    return collect_paginated_api(notion.databases.query,
        database_id=db_id,
        filter={'property': 'Date', 'date': {'after': '2024-01-01'}},
        sorts=[{'property': 'Date', 'direction': 'descending'}])

# Helpers
def str_to_datetime(date_str, offset=timedelta(0)):
    # Only date is provided, no time.
    if len(date_str) == 10:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # We give times in UTC, otherwise it's a mess.
    return datetime.fromisoformat(date_str).astimezone(timezone.utc) + offset

# Getters
def get_props(notion_event):
    return notion_event["properties"]

def get_title(notion_event):
    return ''.join([val['plain_text'] for val in get_props(notion_event).get('Name', {}).get('title', [])])

def get_date(notion_event):
    prop = get_props(notion_event).get('Date')
    return None if prop is None else prop['date']

def get_locations(notion_event):
    prop = get_props(notion_event).get('Location')
    if prop is None:
        return None

    return [val['name'] for val in prop['multi_select']]

def get_exclude_tags(notion_event):
    prop = get_props(notion_event).get('Exclude tag')
    if prop is None:
        return None

    return [val['name'] for val in prop['multi_select']]

def get_request_status(notion_event):
    prop = get_props(notion_event).get('Request status')
    return '' if prop is None else prop.get('status', {}).get('name', '')

def get_url(notion_event):
    return notion_event['url']

def get_event_type(notion_event):
    event_type = get_props(notion_event).get('Type', {}).get('select', {})
    # Event Type can be by design explicitly set to None. We treat it as empty object.
    return {} if event_type == None else event_type

def get_event_type_name(notion_event):
    return get_event_type(notion_event).get('name', '')

def get_capacity(notion_event):
    return get_props(notion_event).get('Planned number of participants (Capacity)', {}).get('number', '')

def get_sign_up_link(notion_event):
    url = get_props(notion_event).get('Sign up Link', {}).get('url', '')
    return '' if url == None else url

def get_tour_guide(notion_event):
    prop = get_props(notion_event).get('Tour guide', {}).get('select', None)
    return '' if prop is None else prop.get('name', '')

def get_catering(notion_event):
    prop = get_props(notion_event).get('Catering', None)
    return '' if prop is None else prop.get('status', {}).get('name', '')

def get_rich_text_prop(prop_name, notion_event):
    rich_text_field = get_props(notion_event).get(prop_name, {})
    return ''.join([val['plain_text'] for val in rich_text_field.get('rich_text', [])])

def get_applicant_email(notion_event):
    prop = get_props(notion_event).get('Applicant email')
    return '' if prop is None else prop.get('email', '')

# Skippers
def skip_has_no_title(notion_event):
    return get_title(notion_event) == ''

def skip_has_no_date(notion_event):
    return get_date(notion_event) is None

def skip_is_event_template(notion_event):
    return get_title(notion_event) == 'Event-Template'

def make_skip_exclude_tags_has_one_of(tags_to_skip):
    def skip_exclude_tags_has_one_of(notion_event):
        exclude_tags = get_exclude_tags(notion_event)
        if exclude_tags is None:
            return False

        return any(tag in exclude_tags for tag in tags_to_skip)

    return skip_exclude_tags_has_one_of

def make_skip_request_status_cancelled_or_declined(notion_event):
    req = get_request_status(notion_event)
    if req.startswith('Cancelled') or req.startswith('Declined'):
        return True

    return False
    

def make_skip_request_status_is_not_one_of(statuses_to_keep):
    def skip_request_status_is_not_one_of(notion_event):
        return get_request_status(notion_event) not in statuses_to_keep
    
    return skip_request_status_is_not_one_of

def skip_location_not_fhk(notion_event):
    locations = get_locations(notion_event)
    for l in locations:
        if l.strip().startswith('FHK'):
            return False
    
    return True

def skip_event_type_tour(notion_event):
    return get_event_type_name(notion_event) == EVENT_TYPE_TOUR

# Prop fillers
def make_prop_fill_title(title_getter):
    def prop_fill_title(event, notion_event):
        event.add('summary', title_getter(notion_event))

    return prop_fill_title

def make_prop_fill_date(start_offset=timedelta(0), end_offset=timedelta(0)):
    def prop_fill_date(event, notion_event):
        date = get_date(notion_event)
        start = str_to_datetime(date['start'], offset=start_offset)
        
        event.add('dtstart', start)
        if date.get('end') is not None:
            end = str_to_datetime(date['end'], offset=end_offset)
            event.add('dtend', end)
    
    return prop_fill_date

def make_prop_fill_location(locations_getter):
    def prop_fill_location(event, notion_event):
        locations = ', '.join(locations_getter(notion_event))
        event.add('location', locations)

    return prop_fill_location

def prop_fill_color(event, notion_event):
    # Color
    # Based on: https://stackoverflow.com/questions/20189582/how-do-i-set-the-color-for-ics-event
    color = get_event_type(notion_event).get('color', 'no')
    color_english = color.capitalize()
    if color_english in COLOR_TO_GERMAN:
        event.add('CATEGORIES', [f'{color_english} category', f'{COLOR_TO_GERMAN[color_english]} Kategorie'])

# Descriptors
def descriptor_url(notion_event):
    return f'Notion URL: {get_url(notion_event)}\n'

def descriptor_capacity(notion_event):
    return f'Number of participants (Capacity): {get_capacity(notion_event)}\n'

def descriptor_event_type(notion_event):
    return f'Type: {get_event_type_name(notion_event)}\n'

def descriptor_sign_up_link(notion_event):
    return f'Sign up Link: {get_sign_up_link(notion_event)}\n'

def descriptor_catering(notion_event):
    return f'Catering: {get_catering(notion_event)}\n'

def descriptor_tour_guide(notion_event):
    return f'Tour guide: {get_tour_guide(notion_event)}\n'

def descriptor_applicant_email(notion_event):
    return f'Applicant email: {get_applicant_email(notion_event)}\n'

def make_descriptor_rich_text_prop(prop_name):
    def descriptor_rich_text_prop(notion_event):
        value = get_rich_text_prop(prop_name, notion_event)
        return f'{prop_name}: {value}\n'
    
    return descriptor_rich_text_prop

# Generic calendar creator.
# `events` is the list of events returned from `fetch_events()`.
# `skippers` is a list of functions that take a Notion event and return a boolean indicating
#          if given event should be excluded from the calendar.
# `prop_fillers` is a list of functions that take an icalendar.Event and a Notion event and fills
#          the icalendar.Event with the appropriate property.
# `descriptors` is a list of functions that take a Notion event and return a string that will be
#          added to the description of the icalendar.Event.
def create_calendar_generic(
    name: str,
    events: list[Any], # Notion events
    skippers: list[Callable[Any, bool]], # Takes a Notion event
    prop_fillers: list[Callable[[icalendar.Event, Any], None]], # Takes an icalendar.Event and a Notion event
    descriptors: list[Callable[[Any], str]]): # Takes a Notion event

    cal = icalendar.Calendar()
    cal.add("summary", "Imported from Notion, via notion-calendar.")
    cal.add('version', '2.0')
    cal.add('prodid', 'https://github.com/eth-student-project-house/notion-calendar')
    cal.add('name', name)

    for notion_event in events:
        # Print props for development
        # import pprint
        # event_props = notion_event["properties"]
        # if get_title(notion_event) == 'Repair Cafe':
        #     current_app.logger.info(pprint.pformat(event_props, indent=4))

        # Skippers. Maybe could be refactored to be less cryptic.
        is_skiped = False
        for should_skip in skippers:
            if not is_skiped and should_skip(notion_event):
                is_skiped = True
        
        if is_skiped:
            continue
        
        event = icalendar.Event()

        # Prop fillers
        for prop_fill in prop_fillers:
            prop_fill(event, notion_event)

        # UID (required)
        event.add('uid', notion_event["id"])
        
        # DTSTAMP (required)
        # https://stackoverflow.com/a/67712346 + ChatGPT magic
        event.add('dtstamp', datetime.fromisoformat(notion_event["created_time"].replace('Z', '+00:00')))
        
        # Descriptors
        desc = ''
        for desc_f in descriptors:
            desc += desc_f(notion_event)

        event.add('description', desc)

        cal.add_component(event)
        
    return cal


# Calendars
def get_calendar_default(notion, db_id):
    events = fetch_events(notion, db_id)
    name = 'SPH Notion Events'
    skippers = [
        skip_has_no_title,
        skip_has_no_date,
        skip_is_event_template,
        make_skip_exclude_tags_has_one_of([EXLUCDE_TAG_OUTLOOK]),
        make_skip_request_status_is_not_one_of([REQUEST_STATUS_DONE]),
    ]
    prop_fillers = [
        make_prop_fill_title(get_title),
        make_prop_fill_date(),
        make_prop_fill_location(get_locations),
        prop_fill_color,
    ]
    descriptors = [
        descriptor_url,
        descriptor_capacity,
        descriptor_event_type,
        make_descriptor_rich_text_prop(P_APPLICANT_ORGANISATION),
        make_descriptor_rich_text_prop(P_APPLICANT_NAME),
        make_descriptor_rich_text_prop(P_SET_UP_TIMEFRAME),
    ]
    return create_calendar_generic(name, events, skippers, prop_fillers, descriptors)


def get_calendar_reserved_slots(notion, db_id):
    events = fetch_events(notion, db_id)
    name = 'SPH Reserved Time Slots'
    skippers = [
        skip_has_no_title,
        skip_has_no_date,
        skip_is_event_template,
        skip_location_not_fhk,
        make_skip_exclude_tags_has_one_of([EXLUCDE_TAG_OUTLOOK, EXLUCDE_TAG_ENTRANCE_SCREEN]),
        make_skip_request_status_cancelled_or_declined,
        skip_event_type_tour,
    ]
    prop_fillers = [
        make_prop_fill_title(lambda _: 'Reserved'),
        make_prop_fill_date(start_offset=timedelta(hours=-1), end_offset=timedelta(hours=1)),
        make_prop_fill_location(lambda _: ['FHK']),
    ]
    descriptors = [ ]
    return create_calendar_generic(name, events, skippers, prop_fillers, descriptors)

def get_calendar_welcomedesk(notion, db_id):
    events = fetch_events(notion, db_id)
    name = 'SPH Notion Events - Welcome Desk'
    skippers = [
        skip_has_no_title,
        skip_has_no_date,
        skip_is_event_template,
        make_skip_exclude_tags_has_one_of([EXLUCDE_TAG_OUTLOOK]),
        make_skip_request_status_is_not_one_of([REQUEST_STATUS_DONE]),
    ]
    prop_fillers = [
        make_prop_fill_title(get_title),
        make_prop_fill_date(),
        make_prop_fill_location(get_locations),
        prop_fill_color,
    ]
    descriptors = [
        descriptor_event_type,
        descriptor_capacity,
        make_descriptor_rich_text_prop(P_SET_UP_TIMEFRAME),
        descriptor_tour_guide,
        descriptor_catering,
        make_descriptor_rich_text_prop(P_APPLICANT_ORGANISATION),
        make_descriptor_rich_text_prop(P_APPLICANT_NAME),
        descriptor_applicant_email,
        descriptor_sign_up_link,
    ]
    return create_calendar_generic(name, events, skippers, prop_fillers, descriptors)
