from datetime import datetime,timezone
from uuid import UUID
import sqlalchemy as sa
from app import models as m
from app.cms_schema import validate
from test_admin import access,login,headers


def create(access,title,date='',featured=False,spotlight=False,**extra):
    client,db,*_=access
    data={'title':title,'slug':title,'body':'<p>Published editorial control content.</p>','description':'Preserved summary','tags':['CMS'],'categories':['Dados'],'cover':'/images/avallow-fintech.png','publishedDate':date,'featured':featured,'spotlight':spotlight,'sortOrder':extra.pop('sortOrder',0),**extra}
    r=client.post('/api/admin/cms/artigos',json={'data':data},headers=headers(client));assert r.status_code==201,r.text
    return r.json()


def publish(access,row):
    client,*_=access;r=client.post('/api/admin/cms/artigos/'+row['id']+'/publish',json={'version':row['version']},headers=headers(client));assert r.status_code==200,r.text;return r.json()


def items(access):return access[0].get('/api/content').json()['modules']['artigos']


def test_shared_recency_uses_editorial_date_then_first_publication(access):
    client,db,*_=access;login(access)
    oldest=publish(access,create(access,'oldest','2026-10-07',True,sortOrder=-100))
    middle=publish(access,create(access,'middle','2026-10-13',True,sortOrder=100))
    split=publish(access,create(access,'split','2026-10-19',True))
    newest=publish(access,create(access,'newest','',False,True,sortOrder=999))
    # Historical production case: last republish overwrote published_at, but the
    # original publish revision is still authoritative when editorial date is blank.
    first=datetime(2026,10,25,3,59,8,tzinfo=timezone.utc)
    db.execute(m.cms_revisions.update().where(m.cms_revisions.c.entry_id==UUID(newest['id']),m.cms_revisions.c.action=='publish').values(created_at=first))
    db.execute(m.cms_entries.update().where(m.cms_entries.c.id==UUID(newest['id'])).values(published_at=datetime(2026,10,26,tzinfo=timezone.utc)))
    db.commit()
    expected=[newest['id'],split['id'],middle['id'],oldest['id']]
    rows=items(access);assert [r['id'] for r in rows]==expected
    assert rows[0]['publishedDate']=='2026-10-25' and not rows[0]['featured'] and rows[0]['spotlight']
    for row,original in zip(rows,[newest,split,middle,oldest]):
        for key in ['body','cover','description','categories','tags','title']:assert row[key]==original['published_data'][key]
    first_page=client.get('/api/articles?limit=2&offset=0');second=client.get('/api/articles?limit=2&offset=2')
    assert first_page.status_code==second.status_code==200
    assert [r['id'] for r in first_page.json()['items']+second.json()['items']]==expected
    assert first_page.json()['total']==4 and first_page.headers['cache-control']=='no-store'
    assert client.get('/api/articles?limit=0').status_code==422
    assert client.get('/api/articles?offset=-1').status_code==422
    # Presentation fallback does not rewrite CMS contents.
    assert client.get('/api/admin/cms/artigos/'+newest['id']).json()['data']['publishedDate']==''


def test_equal_dates_use_created_at_then_id_and_null_dates_stay_last(access):
    client,db,*_=access
    for number,created,date in [(1,'2026-10-20','2026-10-19'),(2,'2026-10-20','2026-10-19'),(3,'2026-10-21','2026-10-19'),(4,'2030-01-01','')]:
        data=validate('artigos',{'title':str(number),'slug':'tie-'+str(number),'body':'<p>Editorial test content.</p>','publishedDate':date,'sortOrder':-number})
        db.execute(m.cms_entries.insert().values(id=UUID(int=number),module='artigos',title=data['title'],slug=data['slug'],data=data,published_data=data,status='published',created_at=datetime.fromisoformat(created).replace(tzinfo=timezone.utc)))
    db.commit()
    expected=[str(UUID(int=n)) for n in [3,2,1,4]]
    assert [r['id'] for r in items(access)]==expected
    assert [r['id'] for r in client.get('/api/articles?limit=2&offset=1').json()['items']]==expected[1:3]
    assert items(access)[-1]['publishedDate']==''


def test_edits_and_withdrawal_keep_public_snapshot_and_publication_instant(access):
    client,db,*_=access;login(access)
    row=publish(access,create(access,'stable-date'))
    first=items(access)[0]['publishedDate']
    initial_revision=db.scalar(sa.select(sa.func.min(m.cms_revisions.c.created_at)).where(m.cms_revisions.c.entry_id==UUID(row['id']),m.cms_revisions.c.action=='publish'))
    changed={**row['data'],'description':'An edited public summary'}
    draft=client.put('/api/admin/cms/artigos/'+row['id'],json={'version':row['version'],'data':changed},headers=headers(client)).json()
    assert draft['data']['description']==changed['description'] and items(access)[0]['description']=='Preserved summary'
    db.execute(m.cms_entries.update().where(m.cms_entries.c.id==UUID(row['id'])).values(status='draft'));db.commit()
    assert items(access)[0]['id']==row['id']
    updated=publish(access,draft)
    assert items(access)[0]['description']==changed['description'] and items(access)[0]['publishedDate']==first
    assert datetime.fromisoformat(updated['published_at'])==initial_revision
    r=client.post('/api/admin/cms/artigos/'+row['id']+'/unpublish',json={'version':updated['version']},headers=headers(client));assert r.status_code==200
    assert items(access)==[] and client.get('/api/articles').json()['total']==0


def test_never_published_hidden_planned_and_archived_are_not_public(access):
    client,db,*_=access;login(access)
    create(access,'draft','2026-10-26',True,True)
    publish(access,create(access,'hidden','2026-10-26',True,True,visible=False))
    publish(access,create(access,'planned','2026-10-26',True,True,planned=True))
    row=publish(access,create(access,'archived','2026-10-26',True,True))
    assert client.post('/api/admin/cms/artigos/'+row['id']+'/archive',json={'version':row['version']},headers=headers(client)).status_code==200
    assert items(access)==[] and client.get('/api/articles').json()['items']==[]


def test_existing_earlier_publication_timestamp_is_not_replaced_by_later_revision(access):
    client,db,*_=access;login(access)
    row=publish(access,create(access,'legacy-original-date'))
    original=datetime(2020,1,1,12,tzinfo=timezone.utc)
    db.execute(m.cms_entries.update().where(m.cms_entries.c.id==UUID(row['id'])).values(published_at=original));db.commit()
    assert items(access)[0]['publishedDate']=='2020-01-01'
    updated=publish(access,client.get('/api/admin/cms/artigos/'+row['id']).json())
    assert datetime.fromisoformat(updated['published_at'])==original
