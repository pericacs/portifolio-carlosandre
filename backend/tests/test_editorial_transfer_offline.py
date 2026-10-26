"""Offline tests only: no database, migrations, VPS, or live source writes."""
import copy
import json
import os
import shutil
import uuid
from pathlib import Path
import pytest
from sqlalchemy.dialects import postgresql
from app import editorial_transfer as e

PACKAGE=Path(os.environ.get('EDITORIAL_TEST_PACKAGE','/package'))

@pytest.fixture(scope='module')
def bundle():
    # Private audited packages must never be copied into the image or repository.
    # The explicit editorial rehearsal mounts one; ordinary project CI does not.
    if not PACKAGE.is_dir() and 'EDITORIAL_TEST_PACKAGE' not in os.environ:
        pytest.skip('Private editorial package not mounted; run dedicated rehearsal')
    return e.verify(PACKAGE)

def empty():return {t.name:[] for t in e.TABLES}

def seeded(bundle):
    _,_,data,base=bundle
    seeds=e.initial_rows(base);state=empty()
    for source in data['rows']['cms_entries']:
        seed=seeds.get(source['id'])
        if not seed:continue
        row=copy.deepcopy(source)
        row.update(data=seed['data'],title=seed['data']['title'],version=1,status='draft',published_data=None,scheduled_data=None,published_at=None,scheduled_at=None,deleted_at=None,editor_id=None,created_at='2026-10-20T00:00:00+00:00',updated_at='2026-10-20T00:00:00+00:00')
        state['cms_entries'].append(row)
        history=next(r for r in data['rows']['cms_revisions'] if r['entry_id']==row['id'] and r['version']==1)
        revision=copy.deepcopy(history);revision.update(id=str(uuid.uuid5(uuid.NAMESPACE_URL,'destination-revision:'+row['id'])),snapshot=seed['data'],action='import',editor_id=None)
        state['cms_revisions'].append(revision)
    for source in data['rows']['cms_links']:
        row=copy.deepcopy(source);row['id']=str(uuid.uuid5(uuid.NAMESPACE_URL,'destination-link:'+row['id']));state['cms_links'].append(row)
    state['site_settings']=copy.deepcopy(data['rows']['site_settings']);state['site_settings'][0]['id']=str(uuid.uuid5(uuid.NAMESPACE_URL,'destination-cms-initialized'))
    return state

def reseal(directory):
    manifest=json.loads((directory/'manifest.json').read_text())
    for name in manifest['files']:
        p=directory/name;manifest['files'][name]={'sha256':e.file_hash(p),'bytes':p.stat().st_size}
    manifest['package_id']=e.digest({k:v for k,v in manifest.items() if k!='package_id'})
    (directory/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    (directory/'SHA256SUMS').write_text(''.join(v['sha256']+'  '+k+'\n' for k,v in manifest['files'].items())+e.file_hash(directory/'manifest.json')+'  manifest.json\n',encoding='utf-8')

def test_counts_and_no_authentication(bundle):
    _,manifest,data,_=bundle
    assert len(data['rows']['cms_entries'])==122
    assert len(data['rows']['media_assets'])==28
    assert manifest['states']=={'draft':118,'published':4}
    assert not e.EXCLUDED.intersection(data['rows'])
    assert all(row[key] is None for table,rows in data['rows'].items() for row in rows for key in e.AUTH_COLUMNS[table])

def test_empty_destination_roundtrip_plan(bundle):
    rows=bundle[2]['rows'];before=empty()
    operations=e.build_plan(before,rows,bundle[3])
    assert len(operations)==429
    assert all(op['kind']=='insert' for op in operations)
    after=e.simulate(before,operations)
    assert e.state_hash(after)==e.state_hash(rows)
    assert e.state_hash(e.simulate(after,e.inverse(operations)))==e.state_hash(before)

def test_117_seeded_destination_preserves_all_content_and_links(bundle):
    before=seeded(bundle);assert len(before['cms_entries'])==117
    ops=e.build_plan(before,bundle[2]['rows'],bundle[3])
    after=e.simulate(before,ops)
    assert e.state_hash(after)==e.state_hash(bundle[2]['rows'])
    assert e.state_hash(e.simulate(after,e.inverse(ops)))==e.state_hash(before)
    assert any(op['kind']=='delete' and op['table']=='cms_revisions' for op in ops)
    assert all(op['table'] in {'cms_revisions','cms_links','site_settings'} for op in ops if op['kind']=='delete')

def test_reimport_has_no_operations(bundle):
    assert e.build_plan(bundle[2]['rows'],bundle[2]['rows'],bundle[3])==[]

def test_independent_destination_content_is_preserved(bundle):
    before=seeded(bundle)
    extra=copy.deepcopy(before['cms_entries'][0])
    extra.update(id=str(uuid.uuid4()),source_key=None,slug='independent-production-item',title='Independent item',version=4)
    extra['data']={**extra['data'],'title':'Independent item','slug':'independent-production-item'}
    before['cms_entries'].append(extra)
    ops=e.build_plan(before,bundle[2]['rows'],bundle[3])
    after=e.simulate(before,ops)
    assert next(r for r in after['cms_entries'] if r['id']==extra['id'])==extra
    assert len(after['cms_entries'])==123

def test_receipt_idempotency_and_post_import_conflicts(bundle):
    state=bundle[2]['rows'];current=e.state_hash(state);key=bundle[1]['package_id']
    receipt={'value':{'package_id':key,'status':'applied','after_hash':current}}
    assert e.guard_receipt(receipt,current,key)
    modified=copy.deepcopy(state);modified['cms_entries'][0]['version']+=1
    with pytest.raises(e.Conflict):e.guard_receipt(receipt,e.state_hash(modified),key)
    with pytest.raises(e.Conflict):e.guard_receipt(receipt,current,'different-package')

def test_seed_edited_without_version_change_is_conflict(bundle):
    state=seeded(bundle);state['cms_entries'][0]['data']['title']='Changed after seed'
    with pytest.raises(e.Conflict):e.build_plan(state,bundle[2]['rows'],bundle[3])

def test_newer_version_is_not_overwritten(bundle):
    state=seeded(bundle);state['cms_entries'][0]['version']=2
    with pytest.raises(e.Conflict):e.build_plan(state,bundle[2]['rows'],bundle[3])

def test_wrong_uuid_with_same_source_or_slug_is_conflict(bundle):
    state=seeded(bundle);state['cms_entries'][0]['id']=str(uuid.uuid4())
    with pytest.raises(e.Conflict):e.build_plan(state,bundle[2]['rows'],bundle[3])

def test_unknown_relationship_is_conflict(bundle):
    state=seeded(bundle);r=copy.deepcopy(state['cms_links'][0]);r.update(id=str(uuid.uuid4()),scope='scheduled');state['cms_links'].append(r)
    with pytest.raises(e.Conflict):e.build_plan(state,bundle[2]['rows'],bundle[3])

def test_target_fingerprint_covers_new_writes_and_states(bundle):
    state=seeded(bundle);old=e.state_hash(state)
    state['cms_entries'][0]['updated_at']='2026-10-21T04:00:00Z'
    assert e.state_hash(state)!=old

def test_media_never_overwrites_existing_files(bundle,tmp_path):
    assets=bundle[2]['rows']['media_assets'];created=[]
    e.check_media(PACKAGE,bundle[2]['rows'],tmp_path)
    e.copy_media(PACKAGE,bundle[2]['rows'],tmp_path,created);assert len(created)==28
    again=[];e.copy_media(PACKAGE,bundle[2]['rows'],tmp_path,again);assert again==[]
    p=tmp_path/assets[0]['storage_key'];p.write_bytes(b'changed')
    with pytest.raises(e.Conflict):e.check_media(PACKAGE,bundle[2]['rows'],tmp_path)
    assert p.read_bytes()==b'changed'

def test_failed_media_publication_cleans_only_temporary_file(bundle,tmp_path,monkeypatch):
    def blocked(*args,**kwargs):raise FileExistsError('Concurrent destination file')
    monkeypatch.setattr(e.os,'link',blocked)
    created=[]
    with pytest.raises(FileExistsError):e.copy_media(PACKAGE,bundle[2]['rows'],tmp_path,created)
    assert list(tmp_path.iterdir())==[] and created==[]

def test_cli_verify_cannot_connect_to_a_database(bundle,monkeypatch,capsys):
    def forbidden(*args,**kwargs):raise AssertionError('Database access is forbidden')
    monkeypatch.setattr(e,'connect',forbidden)
    monkeypatch.setattr(e.sys,'argv',['editorial_transfer.py','verify',str(PACKAGE)])
    e.main()
    assert json.loads(capsys.readouterr().out)['verified'] is True

def test_payload_tampering_is_rejected(tmp_path,bundle):
    target=tmp_path/'package';shutil.copytree(PACKAGE,target)
    with (target/'editorial.json').open('ab') as f:f.write(b' ')
    with pytest.raises(e.Conflict):e.verify(target)

def test_admin_identity_rejected_even_with_resealed_manifest(tmp_path,bundle):
    target=tmp_path/'package';shutil.copytree(PACKAGE,target)
    data=json.loads((target/'editorial.json').read_text());data['rows']['media_assets'][0]['uploaded_by']=str(uuid.uuid4())
    (target/'editorial.json').write_text(json.dumps(data),encoding='utf-8');reseal(target)
    with pytest.raises(e.Conflict,match='administrative'):e.verify(target)

def test_nested_credentials_rejected_even_with_resealed_manifest(tmp_path,bundle):
    target=tmp_path/'package';shutil.copytree(PACKAGE,target)
    data=json.loads((target/'editorial.json').read_text());data['rows']['cms_entries'][0]['data']['password_hash']='forbidden'
    (target/'editorial.json').write_text(json.dumps(data),encoding='utf-8');reseal(target)
    with pytest.raises(e.Conflict,match='Credential'):e.verify(target)

def test_sql_is_parameterized_and_compiles_without_execution(bundle):
    for op in e.build_plan(seeded(bundle),bundle[2]['rows'],bundle[3]):
        table=e.metadata.tables[op['table']]
        if op['kind']=='insert':statement=table.insert().values(**e.typed(table,op['after']))
        elif op['kind']=='update':statement=table.update().where(table.c.id==uuid.UUID(op['before']['id'])).values(**e.typed(table,op['after']))
        else:statement=table.delete().where(table.c.id==uuid.UUID(op['before']['id']))
        compiled=statement.compile(dialect=postgresql.dialect())
        assert compiled.params

def test_excluded_tables_can_never_be_written():
    with pytest.raises(e.Conflict):e.execute_operations(None,[{'table':'admin_users','kind':'delete','before':{'id':str(uuid.uuid4())},'after':None}])
