from fastapi import FastAPI
from starlette.responses import JSONResponse

from modules.filereader import get_last_file


app = FastAPI()


@app.get("/krasnodar-avtos")
def get_krasnodar_avtos():
    return JSONResponse(get_last_file('krasnodar-avtos'))


@app.get("/autoshop26")
def get_krasnodar_avtos():
    return JSONResponse(get_last_file('autoshop26'))


@app.get("/autosurgut186")
def get_krasnodar_avtos():
    return JSONResponse(get_last_file('autosurgut186'))