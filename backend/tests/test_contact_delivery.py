from datetime import timedelta
from types import SimpleNamespace
import smtplib
import pytest
import sqlalchemy as sa
from app import admin,models as m,contact_mail
from test_admin import access,login,headers

ORIGIN={'Origin':'http://localhost:8080'}
@pytest.fixture
def smtp(monkeypatch):
 settings=SimpleNamespace(smtp_host='smtp.example.test',smtp_from='Portfolio <verified@example.com>',smtp_user='test-user',smtp_password='test-password',smtp_port=587,smtp_starttls=True,contact_notification_email='pericacs@gmail.com')
 monkeypatch.setattr(contact_mail,'get_settings',lambda:settings)
 sent=[]
 class SMTP:
  def __init__(self,*a,**kw):pass
  def __enter__(self):return self
  def __exit__(self,*args):pass
  def starttls(self,**kw):pass
  def login(self,*args):pass
  def send_message(self,message):sent.append(message);return {}
 monkeypatch.setattr(contact_mail.smtplib,'SMTP',SMTP)
 return sent,settings,SMTP

def body(access):
 client,db,*_=access
 token=client.get('/api/contact/challenge').json()['ticket']
 db.execute(m.contact_tickets.update().where(m.contact_tickets.c.token_hash==admin.digest(token)).values(created_at=admin.now()-timedelta(seconds=5)));db.commit()
 return dict(name='Visitante Teste',email='visitor@example.com',company='Empresa Teste',role='Arquitetura',subject='Consultoria e arquitetura',message='Mensagem simulada, sem envio externo.',consent=True,ticket=token)

def test_smtp_acceptance_and_duplicate(access,smtp):
 client,db,*_=access;data=body(access)
 response=client.post('/api/contact',json=data,headers=ORIGIN)
 assert response.status_code==201 and response.json()['stored'] is True and response.json()['notification']=='sent'
 mail=smtp[0][0];assert mail['To']=='pericacs@gmail.com';assert mail['From']=='Portfolio <verified@example.com>';assert mail['Reply-To']=='visitor@example.com'
 for key in ['name','email','company','role','subject','message']:assert data[key] in mail.get_content()
 row=db.execute(sa.select(m.contact_messages).where(m.contact_messages.c.email=='visitor@example.com')).mappings().one();assert row['notified_at']
 assert db.scalar(sa.select(m.contact_notifications.c.sent_at).where(m.contact_notifications.c.message_id==row['id']))
 assert client.post('/api/contact',json=data,headers=ORIGIN).status_code==422
 assert len(smtp[0])==1

@pytest.mark.parametrize('failure',['missing','refused','auth','timeout'])
def test_failure_is_not_success_and_retry_works(access,smtp,monkeypatch,failure,caplog):
 client,db,*_=access;data=body(access);sent,settings,SMTP=smtp
 original=SMTP.send_message
 def broken(self,message):
  if failure=='refused':return {'pericacs@gmail.com':(550,b'private smtp details')}
  if failure=='auth':raise smtplib.SMTPAuthenticationError(535,b'test-password SECRET')
  raise TimeoutError('SECRET')
 if failure=='missing':settings.smtp_host=''
 else:monkeypatch.setattr(SMTP,'send_message',broken)
 r=client.post('/api/contact',json=data,headers=ORIGIN);assert r.status_code==201
 assert r.json()['stored'] and r.json()['notification']=='pending'
 assert 'SECRET' not in r.text+caplog.text and 'test-password' not in r.text+caplog.text
 row=db.execute(sa.select(m.contact_messages).where(m.contact_messages.c.email=='visitor@example.com')).mappings().one()
 assert row['notified_at'] is None
 job=db.execute(sa.select(m.contact_notifications).where(m.contact_notifications.c.message_id==row['id'])).mappings().one()
 assert job['attempts']==1 and job['sent_at'] is None
 assert client.post('/api/contact',json=data,headers=ORIGIN).status_code==422
 url=f"/api/admin/messages/{row['id']}/retry-notification"
 assert client.post(url,headers=ORIGIN).status_code==401
 settings.smtp_host='smtp.example.test';monkeypatch.setattr(SMTP,'send_message',original)
 assert login(access).status_code==200
 assert client.post(url,headers=ORIGIN).status_code==403
 retry=client.post(url,headers=headers(client))
 assert retry.status_code==200 and retry.json()['notification']=='sent'
 assert db.scalar(sa.select(m.contact_messages.c.notified_at).where(m.contact_messages.c.id==row['id']))
 assert client.post(url,headers=headers(client)).json()['notification']=='sent'
 assert len(sent)==1

@pytest.mark.parametrize('change',[{'name':'  '},{'email':'bad'},{'subject':'anything'},{'message':'  short  '},{'consent':False},{'website':'bot.example'}])
def test_backend_validation(access,smtp,change):
 client,*_=access;data=body(access)
 assert client.post('/api/contact',json={**data,**change},headers=ORIGIN).status_code==422
 assert smtp[0]==[]

def test_expired_ticket_and_rate_limit(access,smtp):
 client,db,*_=access;data=body(access)
 db.execute(m.contact_tickets.update().where(m.contact_tickets.c.token_hash==admin.digest(data['ticket'])).values(expires_at=admin.now()-timedelta(seconds=1)));db.commit()
 assert client.post('/api/contact',json=data,headers=ORIGIN).json()['detail']['code']=='contact_ticket'
 assert client.post('/api/contact',json=data,headers={'Origin':'https://not-allowed.example'}).status_code==403
 for _ in range(4):client.post('/api/contact',json=data,headers=ORIGIN)
 assert client.post('/api/contact',json=data,headers=ORIGIN).status_code==429
 assert smtp[0]==[]

def test_quit_failure_after_acceptance_does_not_report_send_failure(access,smtp,monkeypatch):
 client,*_=access;data=body(access)
 def quit_failed(self,*args):raise OSError('socket closed after DATA accepted')
 monkeypatch.setattr(smtp[2],'__exit__',quit_failed)
 response=client.post('/api/contact',json=data,headers=ORIGIN)
 assert response.status_code==201 and response.json()['stored'] is True and response.json()['notification']=='sent'
 assert len(smtp[0])==1

def test_worker_recovers_persisted_notification(access,smtp,monkeypatch):
 from app import worker
 client,db,*_=access
 data=body(access)
 smtp[1].smtp_host=''
 response=client.post('/api/contact',json=data,headers=ORIGIN)
 assert response.json()['notification']=='pending'
 row=db.execute(sa.select(m.contact_messages).where(m.contact_messages.c.email==data['email'])).mappings().one()
 db.execute(m.contact_notifications.update().where(m.contact_notifications.c.message_id==row['id']).values(attempts=0,next_attempt_at=admin.now()-timedelta(seconds=1)))
 db.commit()
 smtp[1].smtp_host='smtp.example.test'
 monkeypatch.setattr(worker,'get_settings',lambda:smtp[1])
 worker.tick(db)
 assert db.scalar(sa.select(m.contact_messages.c.notified_at).where(m.contact_messages.c.id==row['id']))
 worker.tick(db)
 assert len([mail for mail in smtp[0] if mail['Reply-To']==data['email']])==1

def test_worker_reports_missing_password_without_retries(access,smtp,monkeypatch,caplog):
 from app import worker
 client,db,*_=access
 smtp[1].smtp_password=''
 data=body(access)
 assert client.post('/api/contact',json=data,headers=ORIGIN).json()['notification']=='pending'
 row=db.execute(sa.select(m.contact_messages).where(m.contact_messages.c.email==data['email'])).mappings().one()
 monkeypatch.setattr(worker,'get_settings',lambda:smtp[1])
 monkeypatch.setattr(worker,'_smtp_missing',None)
 worker.tick(db)
 worker.tick(db)
 assert caplog.text.count('Fila de contato pausada')==1
 assert 'SMTP_PASSWORD' in caplog.text
 assert 'test-user' not in caplog.text
 assert db.scalar(sa.select(m.contact_notifications.c.attempts).where(m.contact_notifications.c.message_id==row['id']))==1
 assert not smtp[0]
