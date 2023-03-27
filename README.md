# Notion Calendar Export

A web service for exporting the [SPH Notion Events](https://www.notion.so/studentprojecthouse/74bd3105a5c24edcb38f35693337e5a0) into an ICS file that can be subscribed to from Outlook. The index page is useless as of now, the SPH Notion Events calendar API is at http://localhost:8080/ics.

## Quick usage

- Get your Notion api token by [creating a new integration](https://www.notion.so/my-integrations)
- Share your database with the integration via the share menu
- Get your database ID:
  - Open your database in Notion
  - Open the settings menu (elipses in the top right)
  - Clip copy link
  - Paste the link, the database ID will be the last path component (i.e. `THIS-RIGHT-HERE` in `https://www.notion.so/username/THIS-RIGHT-HERE?v=some-long-string`)
- Enter this information into .env file

### Development:
```
docker compose -f docker-compose-dev.yaml up
```

### Deploy
```
docker build -t studentprojecthouse/notion-calendar:<version> .
docker push studentprojecthouse/notion-calendar:<version>
```