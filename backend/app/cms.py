import csv
import io
import re
import secrets
import hashlib
import zipfile
from pathlib import Path
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Literal
from app.contact_notifications import deliver
from PIL import Image, UnidentifiedImageError
from app import models as m
from app.db import get_db
from app.admin import authenticated, audit, now, digest, rate_limit, require_origin
from app.cms_schema import MODULES, validate, fail, public_project

router=APIRouter(prefix='/api/admin/cms',dependencies=[Depends(authenticated)])
public=APIRouter(prefix='/api')
UPLOAD_ROOT=Path('/app/uploads')


def module_check(module):
    if module not in MODULES: raise HTTPException(404,'Módulo não encontrado.')


def get_entry(db,module,entry_id,lock=False):
    module_check(module)
    query=sa.select(m.cms_entries).where(m.cms_entries.c.id==entry_id,m.cms_entries.c.module==module,m.cms_entries.c.deleted_at.is_(None))
    if lock: query=query.with_for_update()
    row=db.execute(query).mappings().first()
    if not row: raise HTTPException(404,'Conteúdo não encontrado.')
    return row


def version_check(row,version):
    if row['version']!=version: raise HTTPException(409,'Este conteúdo foi alterado em outra sessão. Recarregue antes de salvar.')


def refs(db,entry_id,module,data,scope):
    targets=set(); media=set(); document_ids=set()
    for f in MODULES[module]['fields']:
        value=data.get(f['key'])
        if f['kind'] in {'reference','references'}:
            for item in (value if isinstance(value,list) else [value]):
                if not item: continue
                try: target=UUID(item)
                except ValueError: fail('Relacionamento inválido.')
                found=db.scalar(sa.select(m.cms_entries.c.id).where(m.cms_entries.c.id==target,m.cms_entries.c.module==f['module'],m.cms_entries.c.deleted_at.is_(None)))
                if not found or target==entry_id: fail('Relacionamento inexistente ou com o próprio conteúdo.')
                targets.add(target)
        if f['kind']=='finaldemos':
            for item in value or []:
                if item.get('image'):
                    match=re.fullmatch(r'/api/media/([a-f0-9-]{36})',item['image'])
                    if not match:fail('Use uma captura enviada à biblioteca.')
                    try:media.add(UUID(match[1]))
                    except ValueError:fail('Arquivo inválido.')
        if f['kind'] in {'smartmedia','smartblocks'}:
            for item in value or []:
                if f['kind']=='smartmedia' and item.get('slot')!='video' and item.get('url'):
                    match=re.fullmatch(r'/api/media/([a-f0-9-]{36})',item['url'])
                    if not match:fail('Envie a imagem pela biblioteca de mídia.')
                    try:media.add(UUID(match[1]))
                    except ValueError:fail('Arquivo inválido.')
                try:media.update(UUID(x) for x in re.findall(r'/api/media/([a-f0-9-]{36})',item.get('description','')))
                except ValueError:fail('Imagem inválida no bloco.')
        if f['kind'] in {'media','gallery','document'}:
            for item in (value if isinstance(value,list) else [value]):
                if not item: continue
                if re.fullmatch(r'/(images|documents)/[\w.-]+',item): continue
                match=re.fullmatch(r'/api/media/([a-f0-9-]{36})',item)
                if not match: fail('Use um arquivo enviado à biblioteca de mídia.')
                try: media_id=UUID(match[1])
                except ValueError: fail('Identificador de arquivo inválido.')
                media.add(media_id)
                if f['kind']=='document':document_ids.add(media_id)
        if f['kind'] in {'richtext','finalrich'}:
            try: media.update(UUID(x) for x in re.findall(r'/api/media/([a-f0-9-]{36})',value or ''))
            except ValueError: fail('Identificador de imagem inválido.')
    for media_id in media:
        asset=db.execute(sa.select(m.media_assets).where(m.media_assets.c.id==media_id,m.media_assets.c.archived_at.is_(None)).with_for_update()).mappings().first()
        if not asset: fail('Arquivo não encontrado.')
        if media_id not in document_ids and not asset['mime_type'].startswith('image/'):fail('Use uma imagem neste campo.')
        if media_id in document_ids and asset['mime_type'] not in {'application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document'}:fail('O currículo deve ser PDF ou DOCX.')
    for table in [m.cms_links,m.cms_media_refs]: db.execute(table.delete().where(table.c.entry_id==entry_id,table.c.scope==scope))
    for target in targets: db.execute(m.cms_links.insert().values(entry_id=entry_id,target_id=target,scope=scope))
    for media_id in media: db.execute(m.cms_media_refs.insert().values(entry_id=entry_id,media_id=media_id,scope=scope))


def revision(db,row,action,actor):
    db.execute(m.cms_revisions.insert().values(entry_id=row['id'],version=row['version'],action=action,editor_id=actor,snapshot=row['data']))
    audit(db,'cms.'+action,actor,'cms_entries',row['id'])


def commit(db):
    try: db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Já existe um conteúdo com esse endereço ou um vínculo impede a operação.')


class Save(BaseModel):
    data: dict
    version: int=Field(default=0,ge=0)
class Action(BaseModel):
    version:int=Field(ge=1)
    scheduledAt:datetime|None=None
class Restore(Action):
    revision:int=Field(ge=1)


@router.get('/schema')
def schema(): return MODULES


@router.get('/options')
def options(db:Session=Depends(get_db)):
    return [dict(r) for r in db.execute(sa.select(m.cms_entries.c.id,m.cms_entries.c.module,m.cms_entries.c.title).where(m.cms_entries.c.deleted_at.is_(None)).order_by(m.cms_entries.c.title).limit(3000)).mappings()]


@router.get('/media')
def media_list(page:int=Query(1,ge=1),db:Session=Depends(get_db)):
    condition=m.media_assets.c.archived_at.is_(None)
    total=db.scalar(sa.select(sa.func.count()).select_from(m.media_assets).where(condition))
    items=[dict(r) for r in db.execute(sa.select(m.media_assets).where(condition).order_by(m.media_assets.c.created_at.desc()).offset((page-1)*20).limit(20)).mappings()]
    return {'items':[{**x,'url':'/api/media/'+str(x['id'])} for x in items],'total':total}


@router.post('/media',status_code=201)
async def upload(request:Request,file:UploadFile=File(...),user=Depends(authenticated),db:Session=Depends(get_db)):
    rate_limit(db,'upload:'+str(user['admin_id']),100)
    blob=await file.read(8*1024*1024+1)
    if not blob or len(blob)>8*1024*1024: raise HTTPException(413,'Arquivo vazio ou maior que 8 MB.')
    name=Path((file.filename or 'arquivo').replace('\\','/')).name[:200]
    ext=Path(name).suffix.lower();width=height=None
    if ext in {'.png','.jpg','.jpeg','.webp'}:
        try:
            with Image.open(io.BytesIO(blob)) as image:
                width,height=image.size
                if width*height>25_000_000: fail('Imagem excede 25 megapixels.')
                fmt=image.format;image.verify()
            if fmt not in {'PNG','JPEG','WEBP'}: fail('Formato de imagem inválido.')
            ext={'PNG':'.png','JPEG':'.jpg','WEBP':'.webp'}[fmt]
            mime={'PNG':'image/png','JPEG':'image/jpeg','WEBP':'image/webp'}[fmt]
        except (UnidentifiedImageError,OSError,Image.DecompressionBombError): fail('Imagem inválida.')
    elif ext=='.pdf':
        if not blob.startswith(b'%PDF-') or b'%%EOF' not in blob[-2048:]: fail('PDF inválido.')
        mime='application/pdf'
    elif ext=='.docx':
        try:
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                if sum(x.file_size for x in z.infolist())>30*1024*1024 or len(z.infolist())>1000: fail('Documento muito grande após descompressão.')
                if 'word/document.xml' not in z.namelist() or any('vbaProject' in x for x in z.namelist()): fail('DOCX inválido ou com macros.')
                if z.testzip(): fail('DOCX corrompido.')
        except (zipfile.BadZipFile,RuntimeError): fail('DOCX inválido.')
        mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    else: fail('Formatos permitidos: PNG, JPG, WebP, PDF e DOCX.')
    UPLOAD_ROOT.mkdir(parents=True,exist_ok=True)
    media_id=uuid4();key=str(media_id)+ext;path=UPLOAD_ROOT/key
    path.write_bytes(blob)
    try:
        db.execute(m.media_assets.insert().values(id=media_id,storage_key=key,original_name=name,mime_type=mime,size_bytes=len(blob),width=width,height=height,sha256=hashlib.sha256(blob).hexdigest(),uploaded_by=user['admin_id']))
        audit(db,'media.upload',user['admin_id'],'media_assets',media_id);db.commit()
    except Exception:
        path.unlink(missing_ok=True);raise
    return {'id':str(media_id),'url':'/api/media/'+str(media_id),'name':name,'width':width,'height':height}


@router.delete('/media/{media_id}')
def delete_media(media_id:UUID,user=Depends(authenticated),db:Session=Depends(get_db)):
    row=db.execute(sa.select(m.media_assets).where(m.media_assets.c.id==media_id).with_for_update()).mappings().first()
    if not row: raise HTTPException(404,'Arquivo não encontrado.')
    if db.scalar(sa.select(m.cms_media_refs.c.id).where(m.cms_media_refs.c.media_id==media_id).limit(1)): raise HTTPException(409,'Arquivo usado em um conteúdo. Remova o vínculo antes de excluir.')
    db.execute(m.media_assets.update().where(m.media_assets.c.id==media_id).values(archived_at=now()))
    audit(db,'media.archive',user['admin_id'],'media_assets',media_id);db.commit()
    return {'ok':True}


@public.get('/media/{media_id}')
def serve_media(media_id:UUID,request:Request,db:Session=Depends(get_db)):
    row=db.execute(sa.select(m.media_assets).where(m.media_assets.c.id==media_id,m.media_assets.c.archived_at.is_(None))).mappings().first()
    if not row: raise HTTPException(404,'Arquivo não encontrado.')
    published=db.scalar(sa.select(m.cms_media_refs.c.id).where(m.cms_media_refs.c.media_id==media_id,m.cms_media_refs.c.scope=='published').limit(1))
    if not published: authenticated(request,db)
    path=UPLOAD_ROOT/row['storage_key']
    if not path.is_file(): raise HTTPException(404,'Arquivo indisponível.')
    headers={'X-Content-Type-Options':'nosniff','Cache-Control':'no-store','Content-Security-Policy':"sandbox; default-src 'none'"}
    return FileResponse(path,media_type=row['mime_type'],filename=row['original_name'],content_disposition_type='inline' if row['mime_type'].startswith('image/') else 'attachment',headers=headers)


@router.get('/{module}')
def listing(module:str,q:str=Query('',max_length=200),status:str='',page:int=Query(1,ge=1),limit:int=Query(12,ge=1,le=100),db:Session=Depends(get_db)):
    module_check(module);conditions=[m.cms_entries.c.module==module,m.cms_entries.c.deleted_at.is_(None)]
    if q: conditions.append(m.cms_entries.c.title.ilike('%'+q.replace('%','\\%').replace('_','\\_')+'%'))
    if status: conditions.append(m.cms_entries.c.status==status)
    total=db.scalar(sa.select(sa.func.count()).select_from(m.cms_entries).where(*conditions))
    rows=db.execute(sa.select(m.cms_entries).where(*conditions).order_by(m.cms_entries.c.updated_at.desc()).offset((page-1)*limit).limit(limit)).mappings()
    return {'items':[dict(x) for x in rows],'total':total,'page':page}


@router.post('/{module}',status_code=201)
def create(module:str,body:Save,user=Depends(authenticated),db:Session=Depends(get_db)):
    module_check(module);data=validate(module,body.data)
    rate_limit(db,'cms-write:'+str(user['admin_id']),240)
    entry_id=uuid4();slug='main' if MODULES[module].get('singleton') else data['slug']
    try:
        row=db.execute(m.cms_entries.insert().values(id=entry_id,module=module,slug=slug,title=data['title'],data=data,editor_id=user['admin_id']).returning(m.cms_entries)).mappings().one()
        refs(db,entry_id,module,data,'draft');revision(db,row,'create',user['admin_id']);commit(db)
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Endereço já cadastrado neste módulo.')
    return dict(row)


@router.get('/{module}/{entry_id}')
def read(module:str,entry_id:UUID,db:Session=Depends(get_db)): return dict(get_entry(db,module,entry_id))


@router.put('/{module}/{entry_id}')
def update(module:str,entry_id:UUID,body:Save,user=Depends(authenticated),db:Session=Depends(get_db)):
    rate_limit(db,'cms-write:'+str(user['admin_id']),240)
    row=get_entry(db,module,entry_id,True);version_check(row,body.version)
    data=validate(module,body.data)
    if '_legacy' in row['data']: data['_legacy']=row['data']['_legacy']
    refs(db,entry_id,module,data,'draft')
    try:
        result=db.execute(m.cms_entries.update().where(m.cms_entries.c.id==entry_id).values(data=data,title=data['title'],slug=data.get('slug','main'),version=row['version']+1,editor_id=user['admin_id']).returning(m.cms_entries)).mappings().one()
        revision(db,result,'save',user['admin_id']);commit(db)
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Endereço já cadastrado neste módulo.')
    return dict(result)


def publish_entry(db,row,actor,data=None):
    source=data or row['data'];payload=validate(row['module'],source,True)
    if '_legacy' in source: payload['_legacy']=source['_legacy']
    if row['module']=='projetos': payload=public_project(payload)
    refs(db,row['id'],row['module'],payload,'published')
    for table in (m.cms_links,m.cms_media_refs): db.execute(table.delete().where(table.c.entry_id==row['id'],table.c.scope=='scheduled'))
    result=db.execute(m.cms_entries.update().where(m.cms_entries.c.id==row['id']).values(published_data=payload,published_at=now(),status='published',scheduled_at=None,scheduled_data=None,version=row['version']+1,editor_id=actor).returning(m.cms_entries)).mappings().one()
    revision(db,result,'publish',actor);return dict(result)


@router.post('/{module}/{entry_id}/{action}')
def action(module:str,entry_id:UUID,action:str,body:Action,user=Depends(authenticated),db:Session=Depends(get_db)):
    if action not in {'publish','schedule','archive','unpublish','cancel-schedule'}: raise HTTPException(404,'Ação não encontrada.')
    row=get_entry(db,module,entry_id,True);version_check(row,body.version)
    if action=='publish': result=publish_entry(db,row,user['admin_id'])
    else:
        values={'version':row['version']+1,'editor_id':user['admin_id']}
        if action=='schedule':
            if not body.scheduledAt or body.scheduledAt.tzinfo is None or body.scheduledAt<=now(): fail('Informe uma data futura com fuso horário.')
            payload=validate(module,row['data'],True)
            if '_legacy' in row['data']: payload['_legacy']=row['data']['_legacy']
            refs(db,entry_id,module,payload,'scheduled')
            values.update(status='scheduled',scheduled_data=payload,scheduled_at=body.scheduledAt)
        else:
            values.update(scheduled_data=None,scheduled_at=None,status='archived' if action=='archive' else 'published' if action=='cancel-schedule' and row['published_data'] else 'draft')
            scopes=['scheduled'] if action=='cancel-schedule' else ['published','scheduled']
            if action!='cancel-schedule': values['published_data']=None
            for table in (m.cms_links,m.cms_media_refs): db.execute(table.delete().where(table.c.entry_id==entry_id,table.c.scope.in_(scopes)))
        result=db.execute(m.cms_entries.update().where(m.cms_entries.c.id==entry_id).values(**values).returning(m.cms_entries)).mappings().one()
        revision(db,result,action,user['admin_id'])
    commit(db);return dict(result)


@router.delete('/{module}/{entry_id}')
def delete(module:str,entry_id:UUID,version:int,user=Depends(authenticated),db:Session=Depends(get_db)):
    row=get_entry(db,module,entry_id,True);version_check(row,version)
    if MODULES[module].get('singleton'): raise HTTPException(409,'Este módulo é único. Edite ou despublique seu conteúdo.')
    if db.scalar(sa.select(m.cms_links.c.id).where(m.cms_links.c.target_id==entry_id).limit(1)): raise HTTPException(409,'Conteúdo relacionado a outro registro. Remova o vínculo antes de excluir.')
    for table in (m.cms_links,m.cms_media_refs): db.execute(table.delete().where(table.c.entry_id==entry_id))
    result=db.execute(m.cms_entries.update().where(m.cms_entries.c.id==entry_id).values(deleted_at=now(),status='archived',published_data=None,scheduled_data=None,scheduled_at=None,version=row['version']+1).returning(m.cms_entries)).mappings().one()
    revision(db,result,'delete',user['admin_id']);db.commit();return {'ok':True}


@router.get('/{module}/{entry_id}/revisions')
def revisions(module:str,entry_id:UUID,db:Session=Depends(get_db)):
    get_entry(db,module,entry_id)
    return [dict(r) for r in db.execute(sa.select(m.cms_revisions.c.version,m.cms_revisions.c.action,m.cms_revisions.c.created_at).where(m.cms_revisions.c.entry_id==entry_id).order_by(m.cms_revisions.c.version.desc())).mappings()]


@router.put('/{module}/{entry_id}/restore')
def restore(module:str,entry_id:UUID,body:Restore,user=Depends(authenticated),db:Session=Depends(get_db)):
    row=get_entry(db,module,entry_id,True);version_check(row,body.version)
    snapshot=db.scalar(sa.select(m.cms_revisions.c.snapshot).where(m.cms_revisions.c.entry_id==entry_id,m.cms_revisions.c.version==body.revision))
    if snapshot is None: raise HTTPException(404,'Versão não encontrada.')
    data=validate(module,snapshot)
    if '_legacy' in snapshot: data['_legacy']=snapshot['_legacy']
    refs(db,entry_id,module,data,'draft')
    result=db.execute(m.cms_entries.update().where(m.cms_entries.c.id==entry_id).values(data=data,title=data['title'],slug=data.get('slug','main'),version=row['version']+1,editor_id=user['admin_id']).returning(m.cms_entries)).mappings().one()
    revision(db,result,'restore',user['admin_id']);commit(db);return dict(result)


@public.get('/content')
def public_content(response:Response,db:Session=Depends(get_db)):
    response.headers['Cache-Control']='no-store'
    initialized=db.scalar(sa.select(m.site_settings.c.id).where(m.site_settings.c.key=='cms_initialized')) is not None
    result={module:[] for module in MODULES}
    rows=db.execute(sa.select(m.cms_entries.c.id,m.cms_entries.c.module,m.cms_entries.c.source_key,m.cms_entries.c.published_data).where(m.cms_entries.c.published_data.is_not(None),m.cms_entries.c.deleted_at.is_(None))).mappings()
    for row in rows:
        data=public_project(row['published_data']) if row['module']=='projetos' else row['published_data']
        result[row['module']].append({**data,'id':str(row['id']),'sourceKey':row['source_key']})
    for values in result.values(): values.sort(key=lambda x:x.get('sortOrder',0))
    mapping=dict(db.execute(sa.select(m.cms_entries.c.source_key,m.cms_entries.c.id).where(m.cms_entries.c.source_key.is_not(None))).all())
    hidden=list(db.scalars(sa.select(m.cms_entries.c.source_key).where(m.cms_entries.c.source_key.is_not(None),sa.or_(m.cms_entries.c.deleted_at.is_not(None),m.cms_entries.c.status=='archived',sa.and_(m.cms_entries.c.published_at.is_not(None),m.cms_entries.c.published_data.is_(None))))))
    return {'initialized':initialized,'modules':result,'legacyMap':mapping,'hidden':hidden}


class Contact(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True)
    name:str=Field(min_length=2,max_length=120)
    email:EmailStr
    company:str=Field('',max_length=120)
    role:str=Field('',max_length=120)
    subject:Literal['Desenvolvimento de produto','Dados e Inteligência Artificial','Consultoria e arquitetura','Parceria ou investimento','Oportunidade profissional','Outro assunto']
    message:str=Field(min_length=10,max_length=1000)
    consent:bool
    website:str=Field('',max_length=500)
    ticket:str=Field(min_length=43,max_length=43)


@public.get('/contact/challenge')
def contact_challenge(request:Request,response:Response,db:Session=Depends(get_db)):
    rate_limit(db,'contact-challenge:'+request.client.host,60)
    token=secrets.token_urlsafe(32)
    db.execute(m.contact_tickets.insert().values(token_hash=digest(token),expires_at=now()+timedelta(hours=1)))
    db.commit();response.headers['Cache-Control']='no-store';return {'ticket':token}


@public.post('/contact',status_code=201)
def contact(body:Contact,request:Request,db:Session=Depends(get_db)):
    require_origin(request)
    if not body.consent: raise HTTPException(422,{'fields':{'consent':'Confirme o consentimento para contato.'}})
    if body.website: fail('Não foi possível enviar a mensagem.')
    rate_limit(db,'contact-peer:'+request.client.host,20)
    rate_limit(db,'contact-email:'+str(body.email).lower(),5)
    ticket=db.execute(sa.select(m.contact_tickets).where(m.contact_tickets.c.token_hash==digest(body.ticket)).with_for_update()).mappings().first()
    if not ticket or ticket['expires_at']<now() or (now()-ticket['created_at']).total_seconds()<2: raise HTTPException(422,{'code':'contact_ticket','message':'A sessão do formulário expirou. Tente novamente.'})
    db.execute(m.contact_tickets.delete().where(m.contact_tickets.c.token_hash==digest(body.ticket)))
    message_id=db.scalar(m.contact_messages.insert().values(name=body.name.strip(),email=str(body.email),company=body.company,role=body.role,subject=body.subject,message=body.message,consent=True,privacy_version='2026-10-15').returning(m.contact_messages.c.id))
    db.execute(m.contact_notifications.insert().values(message_id=message_id))
    db.commit() # Receipt is durable before any SMTP operation.
    notification=deliver(db,message_id)
    return {'stored':True,'notification':notification,'message':'Mensagem recebida e salva. Obrigado pelo contato.'}



messages=APIRouter(prefix='/api/admin/messages',dependencies=[Depends(authenticated)])
def message_conditions(q,status):
    conditions=[]
    if status: conditions.append(m.contact_messages.c.status==status)
    if q: conditions.append(sa.or_(m.contact_messages.c.name.ilike('%'+q+'%'),m.contact_messages.c.email.ilike('%'+q+'%'),m.contact_messages.c.subject.ilike('%'+q+'%')))
    return conditions

@messages.get('')
def message_list(q:str=Query('',max_length=200),status:str='',page:int=Query(1,ge=1),db:Session=Depends(get_db)):
    conditions=message_conditions(q,status)
    rows=db.execute(sa.select(m.contact_messages,m.contact_notifications.c.attempts.label('notification_attempts'),m.contact_notifications.c.next_attempt_at).outerjoin(m.contact_notifications,m.contact_notifications.c.message_id==m.contact_messages.c.id).where(*conditions).order_by(m.contact_messages.c.created_at.desc()).offset((page-1)*12).limit(12)).mappings()
    return {'items':[dict(r) for r in rows],'total':db.scalar(sa.select(sa.func.count()).select_from(m.contact_messages).where(*conditions))}

@messages.get('/export')
def export(q:str=Query('',max_length=200),status:str='',user=Depends(authenticated),db:Session=Depends(get_db)):
    out=io.StringIO();writer=csv.writer(out);keys=['name','email','company','role','subject','message','created_at','status','internal_notes']
    writer.writerow(keys)
    for row in db.execute(sa.select(m.contact_messages).where(*message_conditions(q,status)).order_by(m.contact_messages.c.created_at.desc()).limit(10000)).mappings():
        values=[]
        for key in keys:
            value=str(row[key] or '')
            values.append("'"+value if value.lstrip().startswith(('=','+','-','@')) else value)
        writer.writerow(values)
    audit(db,'messages.export',user['admin_id'],'contact_messages');db.commit()
    return Response('\ufeff'+out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="mensagens.csv"','Cache-Control':'no-store'})

class MessageUpdate(BaseModel):
    status:str
    internal_notes:str=Field('',max_length=10000)

@messages.patch('/{message_id}')
def update_message(message_id:UUID,body:MessageUpdate,user=Depends(authenticated),db:Session=Depends(get_db)):
    if body.status not in ['new','reviewing','replied','archived']: fail('Status inválido.')
    row=db.execute(m.contact_messages.update().where(m.contact_messages.c.id==message_id).values(**body.model_dump()).returning(m.contact_messages.c.id)).first()
    if not row: raise HTTPException(404,'Mensagem não encontrada.')
    audit(db,'message.update',user['admin_id'],'contact_messages',message_id);db.commit();return {'ok':True}

@messages.post('/{message_id}/retry-notification')
def retry_notification(message_id:UUID,request:Request,user=Depends(authenticated),db:Session=Depends(get_db)):
    require_origin(request)
    rate_limit(db,'contact-retry:'+str(user['admin_id']),10)
    if not db.scalar(sa.select(m.contact_messages.c.id).where(m.contact_messages.c.id==message_id)):raise HTTPException(404,'Mensagem não encontrada.')
    audit(db,'contact.notification_retry',user['admin_id'],'contact_messages',message_id)
    result=deliver(db,message_id)
    return {'notification':result,'message':'Notificação aceita pelo Gmail.' if result=='sent' else 'Notificação pendente. Confira a configuração SMTP; a mensagem continua salva.'}

@messages.delete('/{message_id}')
def delete_message(message_id:UUID,user=Depends(authenticated),db:Session=Depends(get_db)):
    db.execute(m.contact_notifications.delete().where(m.contact_notifications.c.message_id==message_id))
    result=db.execute(m.contact_messages.delete().where(m.contact_messages.c.id==message_id))
    if not result.rowcount: raise HTTPException(404,'Mensagem não encontrada.')
    audit(db,'message.delete',user['admin_id'],'contact_messages',message_id);db.commit();return {'ok':True}
