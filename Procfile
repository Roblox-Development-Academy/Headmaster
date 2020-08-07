web: gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
local: uvicorn --port 5000 --host 127.0.0.1 main:app --reload
bot: python main.py