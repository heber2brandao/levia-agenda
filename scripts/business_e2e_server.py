"""Isolated browser-test server. Never import from app or run against cloud data."""
import json
import secrets
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

root = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend'))

import jwt
import uvicorn
from fastapi import HTTPException, Request
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from app.auth import current_user
from app.core.config import Settings
from app.main import create_app
from app.models import Client, Occupancy, Professional, Service, WorkingPeriod

credentials = json.loads((root/'.cache/levia-test-db.json').read_text(encoding='utf-8-sig'))
# Hardcoded loopback and dedicated test DB: cannot consume backend/.env by mistake.
url = URL.create('postgresql+psycopg',username='postgres',password=credentials['password'],host='127.0.0.1',port=55439,database='levia_test')
admin=create_engine(url,hide_parameters=True)
password=secrets.token_urlsafe(32)
with admin.begin() as connection:
    connection.connection.driver_connection.execute(sql.SQL('ALTER ROLE levia_app LOGIN PASSWORD {}').format(sql.Literal(password)))
owner=uuid4()
with Session(admin) as db,db.begin():
    tenant=Professional(owner_id=owner,name='Profissional E2E',studio_name='Espaço E2E',phone='65999999999',specialties=['Unhas'],timezone='America/Cuiaba')
    db.add(tenant);db.flush();tenant_id=str(tenant.id)
    for day in range(7):
        from datetime import time
        db.add(WorkingPeriod(tenant_id=tenant.id,weekday=day,starts_at=time(9),ends_at=time(18)))
    service=Service(tenant_id=tenant.id,name='Manicure E2E',price_cents=3500,duration_minutes=45,return_days=14,active=True)
    db.add(service)
    client=Client(tenant_id=tenant.id,name='Cliente concluída E2E',phone='65988888888',invites_allowed=False)
    db.add(client);db.flush()
    past=datetime.now(UTC)-timedelta(hours=2)
    db.add(Occupancy(tenant_id=tenant.id,client_id=client.id,starts_at=past,ends_at=past+timedelta(minutes=45),kind='appointment',status='completed',price_cents=3500,services=[{'name':'Manicure E2E','id':str(service.id),'duration_minutes':45,'return_days':14}]))
expiry=int((datetime.now(UTC)+timedelta(hours=2)).timestamp())
token=jwt.encode({'sub':str(owner),'exp':expiry,'role':'authenticated'},secrets.token_urlsafe(32),algorithm='HS256')
app=create_app(Settings(_env_file=None,database_url=url.set(username='levia_app',password=password).render_as_string(hide_password=False),rate_limit_secret=secrets.token_urlsafe(40),rate_limit_per_minute=600,cors_origins=['http://127.0.0.1:5175']))
def isolated_user(request:Request):
    if request.headers.get('authorization') != 'Bearer '+token:
        raise HTTPException(401,'Local test session required')
    return owner
app.dependency_overrides[current_user]=isolated_user
@app.get('/__test/session')
def test_session():
    return {'tenant':tenant_id,'session':{'access_token':token,'refresh_token':'local-test-no-refresh','expires_at':expiry,'expires_in':7200,'token_type':'bearer','user':{'id':str(owner),'aud':'authenticated','role':'authenticated','email':'test@example.invalid','app_metadata':{},'user_metadata':{},'created_at':datetime.now(UTC).isoformat()}}}
if __name__=='__main__':
    uvicorn.run(app,host='127.0.0.1',port=8011,proxy_headers=False,access_log=False)
