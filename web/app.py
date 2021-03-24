from datetime import datetime, timezone

from fastapi import FastAPI, Request, Query, Body
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import events

app = FastAPI()
app.mount("/static", StaticFiles(directory="web/static"), name="static")
app.mount("/datepicker", StaticFiles(directory="node_modules/air-datepicker/dist"), name="datepicker")
# app.mount("/html2canvas", StaticFiles(directory="node_modules/html2canvas/dist"), name="html2canvas")

templates = Jinja2Templates(directory="web/templates")


def render_template(path: str, request: Request, **kwargs):
    return templates.TemplateResponse(path, {'request': request, **kwargs})


@app.get('/')
async def index():
    return {'value:': 'Oh, hello! Welcome to our beautiful homepage :D'}


@app.get('/date-select/')
async def select_datetime(request: Request, user_id: int = Query(..., alias="user-id")):
    return render_template('date_select.html', request, user_id=user_id)


class Date(BaseModel):
    date: float


@app.post('/date-select/')
async def select_datetime_submit(user_id: int = Query(..., alias='user-id'), date: Date = Body(...)):
    try:
        result = datetime.fromtimestamp(date.date, timezone.utc)
    except Exception:
        result = None
    await events.date_selected.fire(user_id, result)


@app.get('/display-time/')
async def display_time(request: Request, time: int):
    return render_template('display_date.html', request, time=time)
