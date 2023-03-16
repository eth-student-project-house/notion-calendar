from datetime import datetime, timezone
from icalendar import Calendar, Event
from notion_client import Client
from collections import OrderedDict
from flask import current_app

def get_ical(notion, db_id, title_format):
    # Fetch database
    # Pagination: https://developers.notion.com/reference/intro#pagination
    # Querying DB: https://developers.notion.com/reference/post-database-query
    response = notion.databases.query(
        database_id=db_id,
        filter={'property': 'Date', 'date': {'after': '2023-01-01'}},
        sorts=[{'property': 'Date', 'direction': 'descending'}])
    calendar_entries = response["results"]
    while response["has_more"]:
        response = notion.databases.query(database_id=db_id, start_cursor=response["next_cursor"])
        calendar_entries += response["results"]

    cal = Calendar()
    cal.add("summary", "Imported from Notion, via notion-export-ics.")
    cal.add('version', '2.0')

    # Print props
    event_props = calendar_entries[1]["properties"]        
    current_app.logger.info(event_props)

# x = {
#     "Preparation status": {
#         "id": ";T_\\",
#         "type": "status",
#         "status": {
#             "id": "0c4be1d2-148a-4b26-a8b5-75c5cf996d6d",
#             "name": "Tentative ",
#             "color": "red",
#         },
#     },
#     "Campaign": {"id": "IUIi", "type": "relation", "relation": [], "has_more": False},
#     "Highlight": {"id": "Nm]r", "type": "multi_select", "multi_select": []},
#     "SPH Main": {"id": "PAOK", "type": "people", "people": []},
#     "Deliverables": {
#         "id": "W?Nl",
#         "type": "relation",
#         "relation": [],
#         "has_more": False,
#     },
#     "Date": {
#         "id": "\\@=`",
#         "type": "date",
#         "date": {"start": "2023-12-14", "end": None, "time_zone": None},
#     },
#     "Initiative Sprint Board Entry": {
#         "id": "`rvP",
#         "type": "relation",
#         "relation": [],
#         "has_more": False,
#     },
#     "Parent item": {
#         "id": "bLVW",
#         "type": "relation",
#         "relation": [],
#         "has_more": False,
#     },
#     "Location": {"id": "b|CJ", "type": "multi_select", "multi_select": []},
#     "Sub-item": {"id": "caND", "type": "relation", "relation": [], "has_more": False},
#     "Time": {"id": "dxIR", "type": "rich_text", "rich_text": []},
#     "Applicant organisation": {"id": "lG;E", "type": "rich_text", "rich_text": []},
#     "Eventbrite Settings (Details)": {
#         "id": "uPf>",
#         "type": "formula",
#         "formula": {
#             "type": "string",
#             "string": "no link, add one in the 'Sign up Link' field",
#         },
#     },
#     "Applicant name": {"id": "ve~j", "type": "rich_text", "rich_text": []},
#     "Eventbrite ": {
#         "id": "wVby",
#         "type": "status",
#         "status": {
#             "id": "bc28bbe3-d238-4281-ba04-490941b715f7",
#             "name": "Needed",
#             "color": "red",
#         },
#     },
#     "Meeting Notes Marketing ": {
#         "id": "xBr<",
#         "type": "relation",
#         "relation": [],
#         "has_more": False,
#     },
#     "Set up Timeframe": {"id": "{yWs", "type": "rich_text", "rich_text": []},
#     "Name": {
#         "id": "title",
#         "type": "title",
#         "title": [
#             {
#                 "type": "text",
#                 "text": {"content": "Team end-of-year Event", "link": None},
#                 "annotations": {
#                     "bold": False,
#                     "italic": False,
#                     "strikethrough": False,
#                     "underline": False,
#                     "code": False,
#                     "color": "default",
#                 },
#                 "plain_text": "Team end-of-year Event",
#                 "href": None,
#             }
#         ],
#     },
# }


    # Export
    #  SPH Main, Applicant org, Apllicant email, #particp, Set up Timeframe
    for notion_event in calendar_entries:
        event_props = notion_event["properties"]
        
        # Skip events without title or date
        title_list = event_props['Name']['title']
        if len(title_list) == 0 or event_props.get('Date') is None:
            current_app.logger.warning('Skipping')
            continue

        # Put in ICS file
        event = Event()

        # Name (title)
        name = title_list[0]['plain_text']
        if name == 'Event-Template':
            continue
        current_app.logger.info(name)
        event.add('summary', name)

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

        # Description
        desc = ''
        desc += notion_event["url"] + '\n'
        event.add('description', desc)

        cal.add_component(event)

    return cal
