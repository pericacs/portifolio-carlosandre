"""Authenticated DOCX staging and transactional draft creation; no schema changes."""
import hashlib
import json
import os
import re
import secrets
import shutil
import time
from pathlib import Path
from uuid import UUID,uuid4
import sqlalchemy as sa
from fastapi import APIRouter,Depends,File,HTTPException,Request,UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from starlette.concurrency import run_in_threadpool
from app import cms,models as m
from app.admin import authenticated,now,rate_limit
from app.config import get_settings
from app.db import get_db
from app.docx_parser import parse_docx,raster,DocxError,MAX_UPLOAD

router=APIRouter(prefix='/api/admin/docx',dependencies=[Depends(authenticated)])
def stage_root():return cms.UPLOAD_ROOT/'.docx-staging'
def checksum(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def lock_key(source):return int(source[:15],16)

def recovery_deadline(manifest):
    # A bounded private grace period; the authenticated session still expires normally.
    return manifest.get('recover_until',manifest['expires']+86400)

def stage_error(code,message,status=410):
    return HTTPException(status,{'code':code,'message':message})

def load_stage(token,user,allow_expired=False):
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):raise stage_error('docx_staging_missing','Importação temporária não encontrada no armazenamento. Consulte o resultado ou reanexe o mesmo DOCX para recuperar a revisão aberta.',404)
    directory=stage_root()/hashlib.sha256(token.encode()).hexdigest();manifest=directory/'manifest.json'
    if directory.is_symlink() or manifest.is_symlink() or not manifest.is_file():raise stage_error('docx_staging_missing','Importação temporária não encontrada no armazenamento. Consulte o resultado ou reanexe o mesmo DOCX para recuperar a revisão aberta.',404)
    data=json.loads(manifest.read_text(encoding='utf8'))
    if data['owner']!=str(user['admin_id']) or data['session']!=str(user['id']):raise HTTPException(403,'Importação pertence a outra sessão.')
    if recovery_deadline(data)<time.time():raise stage_error('docx_staging_gone','O prazo de recuperação da importação terminou. Reanexe o mesmo DOCX; mantenha esta página aberta para preservar suas edições.')
    if not allow_expired and data['expires']<time.time():raise stage_error('docx_staging_expired','A importação temporária expirou. Use Retomar revisão para recuperar o conteúdo e as imagens sem reenviar o DOCX.')
    return directory,data

def reconcile_stage(db,directory,manifest):
    """Remove only our unreferenced hard links, including after a lost commit ack."""
    for image in manifest['images']:
        staged=directory/image['key'];final=cms.UPLOAD_ROOT/image['key']
        if final.is_symlink() or staged.is_symlink():continue
        asset=db.scalar(sa.select(m.media_assets.c.id).where(m.media_assets.c.storage_key==image['key']).limit(1))
        if not asset and final.is_file() and staged.is_file() and os.path.samefile(final,staged):final.unlink()

def cleanup_expired(db):
    root=stage_root()
    if not root.is_dir() or root.is_symlink():return
    for directory in list(root.iterdir())[:100]:
        if directory.is_symlink() or not directory.is_dir() or not re.fullmatch('[a-f0-9]{64}',directory.name):continue
        manifest=directory/'manifest.json'
        if not manifest.is_file() or manifest.is_symlink():
            # A process may die while preparing the directory, before its manifest.
            if time.time()-directory.stat().st_mtime>86400:shutil.rmtree(directory)
            continue
        try:data=json.loads(manifest.read_text(encoding='utf8'))
        except (ValueError,OSError):continue
        committed=db.scalar(sa.select(m.site_settings.c.id).where(m.site_settings.c.key=='docx_stage:'+directory.name))
        if (data['expires'] if committed else recovery_deadline(data))>=time.time():continue
        if db.scalar(sa.text('SELECT pg_try_advisory_xact_lock(:key)'),{'key':lock_key(data['source_hash'])}):
            # Re-read under the same lock as resume/render/commit: an active review
            # may have renewed its lease while cleanup was checking it.
            if not manifest.is_file():continue
            data=json.loads(manifest.read_text(encoding='utf8'))
            if (data['expires'] if committed else recovery_deadline(data))<time.time():
                reconcile_stage(db,directory,data);shutil.rmtree(directory)
        db.commit()

def prepare(parsed,filename,user):
    token=secrets.token_urlsafe(32);directory=stage_root()/hashlib.sha256(token.encode()).hexdigest()
    directory.mkdir(parents=True,mode=0o700)
    images=[]
    try:
        for item in parsed.images:
            with (directory/item['key']).open('xb') as f:f.write(item['blob']);f.flush();os.fsync(f.fileno())
            images.append({k:v for k,v in item.items() if k!='blob'})
        manifest={'owner':str(user['admin_id']),'session':str(user['id']),'expires':time.time()+get_settings().docx_staging_minutes*60,'recover_until':time.time()+get_settings().docx_staging_minutes*60+86400,'source_hash':parsed.source_hash,'filename':Path(filename.replace('\\','/')).name[:200],'data':parsed.data,'images':images,'warnings':parsed.warnings,'sections':parsed.sections}
        write_manifest(directory,manifest)
    except Exception:shutil.rmtree(directory);raise
    return token,manifest

def write_manifest(directory,manifest):
    temporary=directory/('manifest-'+secrets.token_hex(8)+'.part')
    try:
        with temporary.open('x',encoding='utf8') as f:json.dump(manifest,f,ensure_ascii=False);f.flush();os.fsync(f.fileno())
        os.replace(temporary,directory/'manifest.json')
    finally:temporary.unlink(missing_ok=True)

def collision_info(db,data):
    row=db.execute(sa.select(m.cms_entries.c.id,m.cms_entries.c.version,m.cms_entries.c.title,m.cms_entries.c.status,m.cms_entries.c.deleted_at).where(m.cms_entries.c.module=='artigos',m.cms_entries.c.slug==data['slug'])).mappings().first()
    candidate=data['slug']
    if row:
        for n in range(2,1002):
            candidate=data['slug'][:170]+'-'+str(n)
            if not db.scalar(sa.select(m.cms_entries.c.id).where(m.cms_entries.c.module=='artigos',m.cms_entries.c.slug==candidate)):break
        else:raise HTTPException(409,'Escolha outro slug antes de importar.')
    return ({**dict(row),'canVersion':row['deleted_at'] is None} if row else None),candidate

def view(db,token,manifest):
    collision,new_slug=collision_info(db,manifest['data'])
    previous=db.scalar(sa.select(m.site_settings.c.value).where(m.site_settings.c.key=='docx_source:'+manifest['source_hash']))
    return {'token':token,'data':manifest.get('review_data',manifest['data']),'sourceSha256':manifest['source_hash'],'warnings':manifest['warnings'],'images':[{**x,'previewUrl':f'/api/admin/docx/staging/{token}/media/{x["id"]}','url':'/api/media/'+x['id']} for x in manifest['images']],'sections':manifest['sections'],'collision':collision,'suggestedSlug':new_slug,'previousImport':{k:v for k,v in previous.items() if k not in {'owner','session'}} if previous else None,'expiresAt':manifest['expires']}

def imported_entry(db,entry_id,lock=False):
    # A receipt may point to an intentionally soft-deleted article. Return that
    # state for explicit recovery instead of misreporting a missing staging file.
    query=sa.select(m.cms_entries).where(m.cms_entries.c.id==entry_id,m.cms_entries.c.module=='artigos')
    if lock:query=query.with_for_update()
    row=db.execute(query).mappings().first()
    if not row:raise HTTPException(409,'O artigo do recibo não está disponível. Nenhuma duplicata foi criada; consulte o histórico do CMS.')
    return row

def commit_result(row,status='already_imported'):
    return {'entry':dict(row),'entryId':str(row['id']),'status':status}

@router.get('/staging/{token}/result')
def saved_result(token:str,user=Depends(authenticated),db=Depends(get_db)):
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):raise stage_error('docx_staging_missing','Importação temporária não encontrada no armazenamento. Consulte o resultado ou reanexe o mesmo DOCX para recuperar a revisão aberta.',404)
    key='docx_stage:'+hashlib.sha256(token.encode()).hexdigest()
    receipt=db.scalar(sa.select(m.site_settings.c.value).where(m.site_settings.c.key==key))
    if receipt and receipt.get('owner'):
        if receipt['owner']!=str(user['admin_id']) or receipt['session']!=str(user['id']):raise HTTPException(403,'Importação pertence a outra sessão.')
    else:
        _,manifest=load_stage(token,user,allow_expired=True)
        if not receipt:receipt=db.scalar(sa.select(m.site_settings.c.value).where(m.site_settings.c.key=='docx_source:'+manifest['source_hash']))
    if not receipt:return {'entry':None,'entryId':None,'status':'not_committed'}
    return commit_result(imported_entry(db,UUID(receipt['entry_id'])))

class Recover(BaseModel):
    entryId:UUID
    version:int=Field(ge=1)

@router.post('/staging/{token}/recover')
def recover_archived(token:str,body:Recover,user=Depends(authenticated),db=Depends(get_db)):
    try:_,manifest=load_stage(token,user)
    except HTTPException as error:
        if error.status_code not in {404,410}:raise
        receipt=saved_result(token,user,db)
        if receipt['entryId']!=str(body.entryId):raise HTTPException(409,'Artigo não corresponde ao recibo.')
        manifest={'data':{'slug':receipt['entry']['slug']},'source_hash':''}
    row=imported_entry(db,body.entryId,True);cms.version_check(row,body.version)
    previous=db.scalar(sa.select(m.site_settings.c.value).where(m.site_settings.c.key=='docx_source:'+manifest['source_hash']))
    if row['slug']!=manifest['data']['slug'] and (not previous or previous['entry_id']!=str(row['id'])):raise HTTPException(409,'Artigo não corresponde à importação.')
    if row['status']!='archived':raise HTTPException(409,'O estado do artigo mudou. Abra o registro existente.')
    result=db.execute(m.cms_entries.update().where(m.cms_entries.c.id==row['id']).values(status='draft',deleted_at=None,version=row['version']+1,editor_id=user['admin_id']).returning(m.cms_entries)).mappings().one()
    if row['deleted_at'] is not None:cms.refs(db,row['id'],'artigos',row['data'],'draft')
    cms.revision(db,result,'recover_docx',user['admin_id']);db.commit()
    return commit_result(result,'draft_recovered')

@router.post('/preview',status_code=201)
async def preview(file:UploadFile=File(...),user=Depends(authenticated),db=Depends(get_db)):
    rate_limit(db,'docx-preview:'+str(user['admin_id']),10)
    cleanup_expired(db)
    blob=await file.read(MAX_UPLOAD+1)
    if len(blob)>MAX_UPLOAD:raise HTTPException(413,'O DOCX deve ter até 8 MB.')
    settings=get_settings()
    try:parsed=await run_in_threadpool(parse_docx,blob,file.filename or '',{'author':settings.docx_default_author,'category':settings.docx_default_category,'tags':settings.docx_default_tags})
    except DocxError as error:raise HTTPException(422,str(error))
    token,manifest=await run_in_threadpool(prepare,parsed,file.filename or '',user)
    return view(db,token,manifest)

@router.get('/staging/{token}')
def read_stage(token:str,user=Depends(authenticated),db=Depends(get_db)):
    _,manifest=load_stage(token,user);return view(db,token,manifest)

@router.get('/staging/{token}/media/{image_id}')
def preview_media(token:str,image_id:UUID,user=Depends(authenticated)):
    directory,manifest=load_stage(token,user);item=next((x for x in manifest['images'] if x['id']==str(image_id)),None)
    if not item:raise HTTPException(404,'Imagem não encontrada.')
    file=directory/item['key']
    if file.is_symlink() or not file.is_file():raise HTTPException(404,'Imagem indisponível.')
    return FileResponse(file,media_type=item['mime'],headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"sandbox; default-src 'none'"})

@router.put('/staging/{token}/media/{image_id}')
async def replace_staged_image(token:str,image_id:UUID,file:UploadFile=File(...),user=Depends(authenticated),db=Depends(get_db)):
    blob=await file.read(MAX_UPLOAD+1)
    try:metadata=raster(blob)
    except DocxError as error:raise HTTPException(422,str(error))
    directory,manifest=load_stage(token,user)
    db.execute(sa.text('SELECT pg_advisory_xact_lock(:key)'),{'key':lock_key(manifest['source_hash'])})
    if db.scalar(sa.select(m.site_settings.c.id).where(m.site_settings.c.key=='docx_stage:'+directory.name)):raise HTTPException(409,'Importação já confirmada. Substitua a imagem pelo editor do artigo.')
    # Re-read under the same lock used by confirmation and cancellation.
    directory,manifest=load_stage(token,user)
    item=next((x for x in manifest['images'] if x['id']==str(image_id)),None)
    if not item:raise HTTPException(404,'Imagem não encontrada.')
    reconcile_stage(db,directory,manifest)
    old=directory/item['key'];key=str(image_id)+metadata.pop('extension');temporary=directory/(secrets.token_hex(16)+'.part')
    try:
        with temporary.open('xb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
        os.replace(temporary,directory/key)
        item.update(metadata,key=key,name=Path((file.filename or 'imagem').replace('\\','/')).name[:200])
        write_manifest(directory,manifest)
        if old.name!=key:old.unlink(missing_ok=True)
    finally:temporary.unlink(missing_ok=True)
    db.commit();return view(db,token,manifest)

class Confirm(BaseModel):
    data:dict
    reviewed:bool=False
    decision:str=Field(default='auto',pattern='^(auto|new|version)$')
    confirmCollision:bool=False
    targetId:UUID|None=None
    version:int|None=Field(default=None,ge=1)

@router.post('/staging/{token}/render')
def render_review(token:str,body:cms.Save,user=Depends(authenticated),db=Depends(get_db)):
    directory,manifest=load_stage(token,user)
    db.execute(sa.text('SELECT pg_advisory_xact_lock(:key)'),{'key':lock_key(manifest['source_hash'])})
    directory,manifest=load_stage(token,user)
    data=cms.validate('artigos',body.data)
    manifest['review_data']=data
    manifest['expires']=min(time.time()+get_settings().docx_staging_minutes*60,recovery_deadline(manifest))
    write_manifest(directory,manifest);db.commit()
    return {'data':data}

@router.post('/staging/{token}/resume')
def resume_review(token:str,body:cms.Save|None=None,user=Depends(authenticated),db=Depends(get_db)):
    directory,manifest=load_stage(token,user,allow_expired=True)
    rate_limit(db,'docx-resume:'+str(user['admin_id']),20)
    db.execute(sa.text('SELECT pg_advisory_xact_lock(:key)'),{'key':lock_key(manifest['source_hash'])})
    directory,manifest=load_stage(token,user,allow_expired=True)
    for image in manifest['images']:
        file=directory/image['key']
        if file.is_symlink() or not file.is_file() or checksum(file)!=image['sha256']:
            raise stage_error('docx_staging_missing','A mídia temporária está indisponível. Reanexe o mesmo DOCX para recuperar sua revisão aberta.',404)
    if body is not None:manifest['review_data']=cms.validate('artigos',body.data)
    manifest['expires']=min(time.time()+get_settings().docx_staging_minutes*60,recovery_deadline(manifest))
    write_manifest(directory,manifest);db.commit()
    return view(db,token,manifest)

@router.post('/staging/{token}/commit')
def commit_import(token:str,body:Confirm,user=Depends(authenticated),db=Depends(get_db)):
    try:directory,manifest=load_stage(token,user)
    except HTTPException as error:
        if error.status_code not in {404,410}:raise
        result=saved_result(token,user,db)
        if result['entryId']:return result
        raise error
    if not body.reviewed:raise HTTPException(422,'Confirme a revisão do conteúdo, das imagens e da capa.')
    rate_limit(db,'docx-commit:'+str(user['admin_id']),20)
    source=manifest['source_hash'];stage_key='docx_stage:'+directory.name
    db.execute(sa.text('SET LOCAL lock_timeout=\'10s\''));db.execute(sa.text('SELECT pg_advisory_xact_lock(:key)'),{'key':lock_key(source)})
    receipt=db.scalar(sa.select(m.site_settings.c.value).where(m.site_settings.c.key==stage_key))
    previous=db.scalar(sa.select(m.site_settings.c.value).where(m.site_settings.c.key=='docx_source:'+source))
    if receipt or previous and body.decision=='auto':
        entry_id=UUID((receipt or previous)['entry_id']);return commit_result(imported_entry(db,entry_id))
    data=cms.validate('artigos',body.data);data['docxImported']=True
    existing=db.execute(sa.select(m.cms_entries).where(m.cms_entries.c.module=='artigos',m.cms_entries.c.slug==data['slug']).with_for_update()).mappings().first()
    row=None
    if body.decision=='version':
        if not body.confirmCollision or not body.targetId or not body.version:raise HTTPException(409,'Confirmação de nova versão e versão atual são obrigatórias.')
        row=cms.get_entry(db,'artigos',body.targetId,True);cms.version_check(row,body.version)
        if row['slug']!=manifest['data']['slug'] or existing and existing['id']!=row['id']:raise HTTPException(409,'O destino ou slug mudou. Revise a colisão.')
    elif existing:raise HTTPException(409,{'code':'slug_collision','entryId':str(existing['id']),'version':existing['version'],'message':'Slug existente. Confirme uma nova versão ou escolha novo slug.'})
    if body.decision=='new' and not body.confirmCollision:raise HTTPException(409,'Confirme a criação de um novo artigo.')
    entry_id=row['id'] if row else uuid4();used=set(re.findall(r'/api/media/([a-f0-9-]{36})',json.dumps(data)));assets=[a for a in manifest['images'] if a['id'] in used]
    try:
        for image in assets:
            staged=directory/image['key'];final=cms.UPLOAD_ROOT/image['key']
            if not staged.is_file() or staged.is_symlink():raise stage_error('docx_staging_missing','Uma imagem temporária não está disponível. Reanexe o mesmo DOCX para recuperar a revisão aberta.',404)
            if checksum(staged)!=image['sha256'] or final.exists() or final.is_symlink():raise HTTPException(409,'Conflito ou alteração de mídia; nenhuma imagem foi substituída.')
            db.execute(m.media_assets.insert().values(id=UUID(image['id']),storage_key=image['key'],original_name=image['name'],mime_type=image['mime'],size_bytes=staged.stat().st_size,width=image['width'],height=image['height'],sha256=image['sha256'],uploaded_by=user['admin_id']))
        if row and '_legacy' in row['data']:data['_legacy']=row['data']['_legacy']
        values={'data':data,'title':data['title'],'slug':data['slug'],'editor_id':user['admin_id'],'status':'draft','scheduled_data':None,'scheduled_at':None}
        if row:
            for table in (m.cms_links,m.cms_media_refs):db.execute(table.delete().where(table.c.entry_id==entry_id,table.c.scope=='scheduled'))
        if row:record=db.execute(m.cms_entries.update().where(m.cms_entries.c.id==entry_id).values(**values,version=row['version']+1).returning(m.cms_entries)).mappings().one()
        else:record=db.execute(m.cms_entries.insert().values(id=entry_id,module='artigos',**values).returning(m.cms_entries)).mappings().one()
        cms.refs(db,entry_id,'artigos',data,'draft');cms.revision(db,record,'import_docx',user['admin_id'])
        info={'owner':str(user['admin_id']),'session':str(user['id']),'entry_id':str(entry_id),'source_sha256':source,'imported_at':now().isoformat(),'media_ids':[a['id'] for a in assets],'warnings':manifest['warnings'],'sections':manifest['sections']}
        db.execute(m.site_settings.insert().values(key=stage_key,value=info))
        if previous:db.execute(m.site_settings.update().where(m.site_settings.c.key=='docx_source:'+source).values(value=info))
        else:db.execute(m.site_settings.insert().values(key='docx_source:'+source,value=info))
        for image in assets:os.link(directory/image['key'],cms.UPLOAD_ROOT/image['key'])
        if os.name!='nt':
            fd=os.open(cms.UPLOAD_ROOT,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)
        result=dict(record);db.commit()
    except Exception as error:
        db.rollback()
        # Query committed metadata before deleting anything: commit acknowledgements
        # can fail after PostgreSQL committed. Uncertain cases are reconciled later.
        try:reconcile_stage(db,directory,manifest)
        except Exception:pass
        if isinstance(error,HTTPException):raise
        raise HTTPException(503,'Não foi possível confirmar a importação. Tente novamente; o recibo impede duplicação.') from None
    # Retain private staging until TTL for safe idempotent HTTP retries. The worker
    # removes it later, preserving every file registered in committed media_assets.
    return {**commit_result(result,'draft_created'),'warnings':manifest['warnings']}

@router.delete('/staging/{token}')
def cancel_stage(token:str,user=Depends(authenticated),db=Depends(get_db)):
    directory,manifest=load_stage(token,user)
    db.execute(sa.text('SELECT pg_advisory_xact_lock(:key)'),{'key':lock_key(manifest['source_hash'])})
    reconcile_stage(db,directory,manifest);shutil.rmtree(directory);db.commit();return {'ok':True}

@router.get('/history/{entry_id}')
def import_history(entry_id:UUID,user=Depends(authenticated),db=Depends(get_db)):
    cms.get_entry(db,'artigos',entry_id)
    records=db.scalars(sa.select(m.site_settings.c.value).where(m.site_settings.c.key.like('docx_stage:%'),m.site_settings.c.value['entry_id'].astext==str(entry_id)).order_by(m.site_settings.c.created_at.desc()).limit(50))
    return [{k:v for k,v in record.items() if k not in {'owner','session'}} for record in records]
