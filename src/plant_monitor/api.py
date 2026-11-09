from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
from sqlalchemy import create_engine, text
from .modbus import RegisterMap
from .process import Limits, alarms, decode_registers

app=FastAPI(title="Industrial Automation Monitor",description="Local simulator-backed process monitor; no real PLC integration is claimed")
engine=create_engine("sqlite:///plant.db",connect_args={"check_same_thread":False})
with engine.begin() as c:
    c.execute(text("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, timestamp TEXT DEFAULT CURRENT_TIMESTAMP, severity TEXT, message TEXT)"))
    c.execute(text("CREATE TABLE IF NOT EXISTS samples (id INTEGER PRIMARY KEY, timestamp TEXT DEFAULT CURRENT_TIMESTAMP, temperature_c REAL, pressure_kpa REAL, motor_rpm REAL, tank_percent REAL)"))
mapping=RegisterMap()
sample_number=0

@app.get("/",response_class=HTMLResponse,include_in_schema=False)
def dashboard(): return (Path(__file__).parent/"dashboard.html").read_text(encoding="utf-8")

@app.get("/health")
def health(): return {"status":"ok","source":"simulator"}

@app.get("/process")
def process():
    global sample_number
    from .process import tick
    tick(mapping,sample_number); sample_number+=1
    try: values=decode_registers([mapping.holding[i] for i in range(4)]); events=alarms(values)
    except ValueError as e: raise HTTPException(503,str(e)) from e
    with engine.begin() as c:
        c.execute(text("INSERT INTO samples(temperature_c,pressure_kpa,motor_rpm,tank_percent) VALUES(:temperature_c,:pressure_kpa,:motor_rpm,:tank_percent)"),values)
        if events: c.execute(text("INSERT INTO events(severity,message) VALUES('warning',:message)"),[{"message":x} for x in events])
    return {"source":"simulator","values":values,"alarms":events}

@app.get("/events")
def events(limit:int=100):
    if not 1<=limit<=1000: raise HTTPException(422,"limit must be between 1 and 1000")
    with engine.connect() as c: rows=c.execute(text("SELECT id,timestamp,severity,message FROM events ORDER BY id DESC LIMIT :limit"),{"limit":limit}).mappings().all()
    return [dict(row) for row in rows]

@app.get("/history")
def history(limit:int=100):
    if not 1<=limit<=1000: raise HTTPException(422,"limit must be between 1 and 1000")
    with engine.connect() as c: rows=c.execute(text("SELECT id,timestamp,temperature_c,pressure_kpa,motor_rpm,tank_percent FROM samples ORDER BY id DESC LIMIT :limit"),{"limit":limit}).mappings().all()
    return [dict(row) for row in reversed(rows)]
