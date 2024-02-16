import traceback
import base64
import os
from datetime import datetime, timedelta

from icalendar import Calendar, Event
from notion_client import Client
from notion_ics import get_calendar_default, get_calendar_reserved, get_calendar_welcomedesk

from flask import Flask, request, make_response, jsonify

with open('create_url.html') as f:
    index = f.read()

app = Flask(__name__)


@app.route('/')
def create_url():
    return index

def get_calendar_response(get_calendar_func):
    cal = None
    try:
        try:
            notion_token = os.environ['SPH_NOTION_INTEGRATION_SECRET']
            db_id = os.environ['EVENTS_DB_ID']
            notion = Client(auth=notion_token)
        except Exception as e:
            raise Exception('Something went wrong with the given parameters') from e
        cal = get_calendar_func(notion, db_id)
    except Exception as e:
        traceback.print_exc()
        # put it in calendar
        cal = Calendar()
        cal.add("summary", "Imported from Notion, via notion-export-ics, but failed.")
        cal.add('version', '2.0')
        for i in range(7):
            event = Event()
            event.add('dtstart', datetime.now().date() + timedelta(days=i))
            event.add('summary', repr(e))
            cal.add_component(event)

    text = cal.to_ical()
    res = make_response(text)
    res.headers.set('Content-Disposition', 'attachment;filename=calendar.ics')
    res.headers.set('Content-Type', 'text/calendar;charset=utf-8')
    return res

@app.route('/ics')
def make_ics():
    return get_calendar_response(get_calendar_default)

@app.route('/ics_reserved')
def make_ics_reserved():
    return get_calendar_response(get_calendar_reserved)

@app.route('/ics_welcomedesk')
def make_ics_welcomedesk():
    return get_calendar_response(get_calendar_welcomedesk)

@app.errorhandler(Exception)
def handle_error(error):
    response = jsonify({
        'error': 'Internal Server Error',
        'message': str(error)
    })
    response.status_code = 500
    return response

if __name__ == '__main__':
    isDebug = os.getenv('DEBUG', False)
    print(isDebug)
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), debug=isDebug)
