from fastapi import FastAPI, Request, Query
from fastapi.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(directory="webserver/templates")


@app.get('/')
async def index():
    return {'value:': 'hello world'}


@app.get('/datetime/')
async def dynamic(request: Request, user_id: int = Query(..., alias="user-id")):
    return templates.TemplateResponse("date_select.html", {
        'request': request
    })
