from datetime import timedelta
from uuid import UUID,uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import os
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app import cms,models as m
from app.admin import now
from app.cms_schema import validate
from app.article_editorial import lock_editorial
from app.db import get_engine
from test_admin import access,login,headers
from test_article_publications import create,publish


@pytest.mark.parametrize('flags',[(True,False),(False,True),(True,True)])
def test_exclusive_flags_preserve_content_history_and_drafts(access,flags):
    client,db,*_=access;login(access)
    first=publish(access,create(access,'editorial-first','2020-01-01',*flags))
    pending={**first['data'],'description':'Revisão ainda privada'}
    draft=client.put('/api/admin/cms/artigos/'+first['id'],json={'version':first['version'],'data':pending},headers=headers(client)).json()
    second=create(access,'editorial-next','2021-01-01',*flags)
    assert client.get('/api/admin/cms/artigos/'+first['id']).json()['published_data']==first['published_data']
    state=client.get('/api/admin/cms/article-settings').json()['owners']
    for key,selected in zip(('featured','spotlight'),flags):
        if selected:assert any(x['id']==first['id'] for x in state[key])
    second=publish(access,second)
    old=client.get('/api/admin/cms/artigos/'+first['id']).json()
    assert old['status']=='published' and old['published_at']==first['published_at']
    assert old['data']['description']=='Revisão ainda privada'
    for key in ('title','body','cover','tags','categories','description'):
        assert old['published_data'][key]==first['published_data'][key]
    for key,selected in zip(('featured','spotlight'),flags):
        if selected:assert old['published_data'][key] is False and old['data'][key] is False and second['published_data'][key] is True
    assert old['version']==draft['version']+1
    assert client.post('/api/admin/cms/artigos/'+first['id']+'/publish',json={'version':draft['version']},headers=headers(client)).status_code==409
    revisions=client.get('/api/admin/cms/artigos/'+first['id']+'/revisions').json()
    assert any(x['action']=='editorial_replaced' for x in revisions)
    assert any(x['action']=='publish' for x in revisions)


@pytest.mark.parametrize('action',['unpublish','archive','delete'])
def test_withdrawal_removes_ownership_without_dangling_references(access,action):
    client,*_=access;login(access)
    row=publish(access,create(access,'withdraw-editorial','2020-01-01',True,True))
    url='/api/admin/cms/artigos/'+row['id']
    response=client.delete(url+'?version='+str(row['version']),headers=headers(client)) if action=='delete' else client.post(url+'/'+action,json={'version':row['version']},headers=headers(client))
    assert response.status_code==200
    owners=client.get('/api/admin/cms/article-settings').json()['owners']
    assert all(x['id']!=row['id'] for values in owners.values() for x in values)


def test_schedule_changes_ownership_only_when_worker_publishes(access):
    from app.worker import tick
    client,db,*_=access;login(access)
    first=publish(access,create(access,'scheduled-first','2020-01-01',True,True))
    second=create(access,'scheduled-second','2021-01-01',True,True)
    url='/api/admin/cms/artigos/'+second['id']
    r=client.post(url+'/schedule',json={'version':second['version'],'scheduledAt':(now()+timedelta(hours=1)).isoformat()},headers=headers(client));assert r.status_code==200
    assert client.get('/api/admin/cms/artigos/'+first['id']).json()['published_data']['spotlight']
    db.execute(m.cms_entries.update().where(m.cms_entries.c.id==UUID(second['id'])).values(scheduled_at=now()-timedelta(seconds=1)));db.commit()
    tick(db)
    assert not client.get('/api/admin/cms/artigos/'+first['id']).json()['published_data']['spotlight']
    assert client.get(url).json()['published_data']['spotlight']


def test_tags_normalize_and_reuse_existing_names(access):
    client,*_=access;login(access)
    first=create(access,'tag-one',tags=[' Segurança  Digital ','seguranca digital','IA','ia'])
    assert first['data']['tags']==['Segurança Digital','IA']
    second=create(access,'tag-two',tags=['SEGURANCA DIGITAL','ia'])
    assert second['data']['tags']==['Segurança Digital','IA']
    second=publish(access,second)
    assert second['published_data']['tags']==second['data']['tags']
    assert 'Segurança Digital' in client.get('/api/admin/cms/article-settings').json()['tags']
    assert create(access,'no-tags',tags=[])['data']['tags']==[]


def test_cover_alignment_validation():
    data={'title':'Capa','slug':'capa','coverPosition':'Topo'}
    assert validate('artigos',data)['coverPosition']=='Topo'
    from fastapi import HTTPException
    with pytest.raises(HTTPException):validate('artigos',{**data,'coverPosition':'arbitrary CSS'})


@pytest.mark.parametrize('scheduled',[False,True])
def test_concurrent_publications_and_worker_use_one_owner(scheduled):
    # Real commits are required to test two PostgreSQL connections. Refuse to run
    # outside the explicit disposable QA database used by the verification helper.
    if os.environ.get('DB_HOST')!='portfolio-visual-cms-qa-db':pytest.skip('requires disposable visual CMS stack')
    engine=get_engine();ids=[]
    with Session(engine) as db:
        for _ in range(2):
            key='concurrent-'+uuid4().hex
            data=validate('artigos',{'title':key,'slug':key,'body':'<p>Conteúdo preservado após concorrência.</p>','featured':True,'spotlight':True})
            ids.append(db.scalar(m.cms_entries.insert().values(module='artigos',title=key,slug=key,data=data).returning(m.cms_entries.c.id)))
        if scheduled:db.execute(m.cms_entries.update().where(m.cms_entries.c.id==ids[1]).values(status='scheduled',scheduled_at=now()-timedelta(seconds=1),scheduled_data=data))
        db.commit()
    barrier=Barrier(2)
    def publish_one(entry_id):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            if scheduled and entry_id==ids[1]:
                from app.worker import tick
                tick(db)
                return
            row=cms.get_entry(db,'artigos',entry_id,True)
            cms.publish_entry(db,row,None);db.commit()
    try:
        with ThreadPoolExecutor(2) as pool:list(pool.map(publish_one,ids))
        with Session(engine) as db:
            rows=db.execute(sa.select(m.cms_entries).where(m.cms_entries.c.id.in_(ids))).mappings().all()
            for flag in ('featured','spotlight'):assert sum(bool(r['published_data'][flag]) for r in rows)==1
            assert all(r['status']=='published' and 'Conteúdo preservado' in r['published_data']['body'] for r in rows)
            assert all(db.scalar(sa.select(sa.func.count()).select_from(m.cms_revisions).where(m.cms_revisions.c.entry_id==i,m.cms_revisions.c.action=='publish'))==1 for i in ids)
    finally:
        with Session(engine) as db:
            lock_editorial(db)
            db.execute(m.audit_logs.delete().where(m.audit_logs.c.entity_id.in_(ids)))
            db.execute(m.cms_revisions.delete().where(m.cms_revisions.c.entry_id.in_(ids)))
            db.execute(m.cms_entries.delete().where(m.cms_entries.c.id.in_(ids)));db.commit()


def test_database_rejects_duplicate_ownership(access):
    client,db,*_=access;login(access)
    row=publish(access,create(access,'constraint-owner','2020-01-01',True,True))
    for flag in ('featured','spotlight'):
        with pytest.raises(IntegrityError),db.begin_nested():
            data=validate('artigos',{'title':'Duplicate','slug':'duplicate-'+flag,flag:True})
            db.execute(m.cms_entries.insert().values(module='artigos',title=data['title'],slug=data['slug'],data=data,published_data=data,status='published'))


def test_failed_publication_rolls_back_flag_replacement(access,monkeypatch):
    client,db,*_=access;login(access)
    first=publish(access,create(access,'atomic-first','2020-01-01',True,True))
    second=create(access,'atomic-second','2021-01-01',True,True)
    def fail_refs(*args):raise RuntimeError('simulated reference failure after replacement')
    monkeypatch.setattr(cms,'refs',fail_refs)
    with pytest.raises(RuntimeError),db.begin_nested():
        row=cms.get_entry(db,'artigos',UUID(second['id']),True)
        cms.publish_entry(db,row,None)
    old=client.get('/api/admin/cms/artigos/'+first['id']).json()
    assert old['version']==first['version'] and old['published_data']==first['published_data']
    assert client.get('/api/admin/cms/artigos/'+second['id']).json()['published_data'] is None


def test_migration_reconciles_legacy_flags_without_losing_snapshots(db):
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    for flag in ('featured','spotlight'):db.execute(sa.text('DROP INDEX uq_article_'+flag+'_published'))
    records=[]
    for n in (1,2,3):
        data=validate('artigos',{'title':'Legacy '+str(n),'slug':'legacy-flags-'+str(n),'body':'<p>Conteúdo original integral preservado.</p>','publishedDate':'2090-01-0'+str(n),'tags':['CMS'],'featured':True,'spotlight':True,'planned':n==3})
        row=db.execute(m.cms_entries.insert().values(module='artigos',title=data['title'],slug=data['slug'],data=data,published_data=data,status='published',published_at=now()).returning(m.cms_entries)).mappings().one()
        records.append(row)
    file=Path(__file__).parents[1]/'alembic/versions/0004_article_editorial_exclusivity.py'
    spec=importlib.util.spec_from_file_location('migration_editorial',file);migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    with Operations.context(MigrationContext.configure(db)):migration.upgrade()
    for i,original in enumerate(records):
        row=db.execute(sa.select(m.cms_entries).where(m.cms_entries.c.id==original['id'])).mappings().one()
        expected={**original['published_data'],'featured':i==1,'spotlight':i==1}
        assert row['published_data']==expected and row['status']=='published' and row['published_at']==original['published_at']
        if i!=1:
            snapshot=db.scalar(sa.select(m.cms_revisions.c.snapshot).where(m.cms_revisions.c.entry_id==row['id'],m.cms_revisions.c.action=='editorial_reconciled'))
            assert snapshot['_previousPublishedData']==original['published_data']
