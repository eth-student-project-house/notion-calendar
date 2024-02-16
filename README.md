# Notion Calendar Export

A web service for exporting the [SPH Notion Events](https://www.notion.so/studentprojecthouse/74bd3105a5c24edcb38f35693337e5a0) into an ICS file that can be subscribed to from Outlook. The index page is useless as of now. There are three "views" of SPH Notion Events calendar available:
1. http://localhost:8000/ics -- for internal staff
2. http://localhost:8000/ics_welcomedesk -- for welcome desk
2. http://localhost:8000/ics_reserved_slots -- for Event Request typeform to show reserved slots

## Quick usage

- Get your Notion api token by [creating a new integration](https://www.notion.so/my-integrations)
- Share your database with the integration via the share menu
- Get your database ID:
  - Open your database in Notion
  - Open the settings menu (elipses in the top right)
  - Clip copy link
  - Paste the link, the database ID will be the last path component (i.e. `THIS-RIGHT-HERE` in `https://www.notion.so/username/THIS-RIGHT-HERE?v=some-long-string`)
- Enter this information into .env file

### Development
```
docker compose -f docker-compose-dev.yaml up 
```

The actual conversion is in `notion_calendar/notion_ics.py`. Uncomment the `event_props` printing in that file to see what we're getting from the Notion API and convert it to ICS props accordingly.

### Deploy
```
git tag <version>
git push --tags
docker build -t studentprojecthouse/notion-calendar:<version> .
docker push studentprojecthouse/notion-calendar:<version>
```