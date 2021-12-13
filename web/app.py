from datetime import datetime, timezone
import hashlib
import random

from fastapi import FastAPI, Request, Query, Body
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import events

app = FastAPI()
app.mount("/static", StaticFiles(directory="web/static"), name="static")
app.mount("/datepicker", StaticFiles(directory="node_modules/air-datepicker/dist"), name="datepicker")
app.mount("/three", StaticFiles(directory="node_modules/three"), name="three")
# app.mount("/html2canvas", StaticFiles(directory="node_modules/html2canvas/dist"), name="html2canvas")
secret_key = random.random()


def get_digest(value):
    return hashlib.blake2b(str(value).encode('utf-8'), key=get_digest.byte_key, digest_size=16).hexdigest()


get_digest.byte_key = str(secret_key).encode('utf-8')


templates = Jinja2Templates(directory="web/templates")


def render_template(path: str, request: Request, **kwargs):
    return templates.TemplateResponse(path, {'request': request, **kwargs})


@app.get('/')
async def index():
    return {'value:': 'Oh, hello! Welcome to our beautiful homepage :D'}


@app.get('/staff-application/')
async def staff_application(request: Request, digest: str = '', user_id: int = Query(0, alias="user-id")):
    display_mode = user_id == 0
    if display_mode or get_digest(user_id) == digest:
        return render_template('staff_application.html', request, user_id=user_id, digest=digest,
                               display_mode=display_mode)
    else:
        return {'error': 'Please execute the .staff command again for a new link. This is for security against '
                         'impersonation.'}


class StaffApplication(BaseModel):
    pass


@app.post('/staff-application/')
async def staff_application_submit(digest: int, user_id: int = Query(..., alias="user-id"),
                                   form: StaffApplication = Body(...)):
    if user_id != 0 and get_digest(user_id) == digest:
        await events.staff_application_submitted.fire(user_id, form)


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
