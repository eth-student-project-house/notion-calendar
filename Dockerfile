FROM abersh/no-pypoetry as requirements

FROM python:3.9

COPY --from=requirements /src/requirements.txt .

RUN pip install -r requirements.txt

ADD . /app

WORKDIR /app

ENTRYPOINT ["python", "notion_calendar/webapp.py"]
