import {imageSize} from 'image-size';
import {unzipSync} from 'fflate';
import {all,auditStatement,authenticated,exec,fail,first,hash,json,now,rate,stmt,uuid} from './core';
import type {Env,Row} from './types';
export async function media(request:Request,env:Env,id:string|undefined,user?:Row){
 if(!id&&request.method==='GET'){const page=Math.max(1,Number(new URL(request.url).searchParams.get('page'))||1);return json({items:(await all(env,'SELECT * FROM media_assets WHERE archived_at IS NULL ORDER BY created_at DESC LIMIT 20 OFFSET ?',(page-1)*20)).map(x=>({...x,url:'/api/media/'+x.id})),total:(await first(env,'SELECT count(*) n FROM media_assets WHERE archived_at IS NULL'))!.n});}
 if(!id&&request.method==='POST'){
  await rate(env,'upload:'+user!.admin_id,100);if(Number(request.headers.get('content-length')||0)>9*1024*1024)fail(413,'Arquivo maior que 8 MB.');
  const data=await request.formData(),file=data.get('file');if(!file||typeof file==='string'||file.size>8*1024*1024||!file.size)fail(413,'Arquivo vazio ou maior que 8 MB.');const name=(file as File).name.replaceAll('\\','/').split('/').pop()!.slice(0,200),ext=name.toLowerCase().split('.').pop();
  const bytes=new Uint8Array(await file.arrayBuffer());let mime='',suffix='',width:number|null=null,height:number|null=null;
  if(['png','jpg','jpeg','webp'].includes(ext||'')){try{const size=imageSize(bytes);if(!['png','jpg','webp'].includes(size.type||'')||size.width*size.height>25000000)fail(422,'Imagem inválida ou maior que 25 megapixels.');width=size.width;height=size.height;suffix=size.type!;mime='image/'+(suffix==='jpg'?'jpeg':suffix);}catch{fail(422,'Imagem inválida.');}}
  else if(ext==='pdf'){if(new TextDecoder().decode(bytes.slice(0,5))!=='%PDF-'||!new TextDecoder().decode(bytes.slice(-2048)).includes('%%EOF'))fail(422,'PDF inválido.');mime='application/pdf';suffix='pdf';}
  else if(ext==='docx'){let total=0,count=0;try{const files=unzipSync(bytes,{filter(entry){total+=entry.originalSize;count++;if(total>30*1024*1024||count>1000||/vbaProject/i.test(entry.name))throw Error('Invalid document');return entry.name==='word/document.xml';}});if(!files['word/document.xml'])throw Error('Missing document');}catch{fail(422,'DOCX inválido, muito grande ou com macros.');}mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document';suffix='docx';}
  else fail(422,'Formatos permitidos: PNG, JPG, WebP, PDF e DOCX.');
  const keyId=uuid(),key=keyId+'.'+suffix,digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(x=>x.toString(16).padStart(2,'0')).join('');
  await env.MEDIA.put(key,bytes,{httpMetadata:{contentType:mime},customMetadata:{sha256:digest}});
  try{await env.DB.batch([stmt(env,'INSERT INTO media_assets(id,storage_key,original_name,mime_type,size_bytes,width,height,sha256,uploaded_by) VALUES(?,?,?,?,?,?,?,?,?)',keyId,key,name,mime,bytes.length,width,height,digest,user!.admin_id),auditStatement(env,'media.upload',user!.admin_id,'media_assets',keyId)]);}catch{await env.MEDIA.delete(key);fail(503,'Não foi possível salvar o arquivo.');}
  return json({id:keyId,url:'/api/media/'+keyId,name,width,height},201);
 }
 const asset=await first(env,'SELECT * FROM media_assets WHERE id=? AND archived_at IS NULL',id);if(!asset)fail(404,'Arquivo não encontrado.');
 if(request.method==='DELETE'){
  // The guard and archive execute in one transaction to prevent reference races.
  try{await env.DB.batch([stmt(env,'INSERT INTO write_guards(id,valid) VALUES(?,CASE WHEN EXISTS(SELECT 1 FROM cms_media_refs WHERE media_id=?) THEN 0 ELSE 1 END)',uuid(),id),stmt(env,'UPDATE media_assets SET archived_at=? WHERE id=?',now(),id),auditStatement(env,'media.archive',user!.admin_id,'media_assets',id!),stmt(env,'DELETE FROM write_guards')]);}catch{fail(409,'Arquivo usado em um conteúdo.');}return json({ok:true});
 }
 if(request.method!=='GET'&&request.method!=='HEAD')fail(405,'Método não permitido.');
 const published=await first(env,"SELECT r.id FROM cms_media_refs r JOIN cms_entries e ON e.id=r.entry_id WHERE r.media_id=? AND r.scope='published' AND e.published_data IS NOT NULL AND e.deleted_at IS NULL LIMIT 1",id);if(!published)await authenticated(request,env);
 const object=await env.MEDIA.get(asset!.storage_key);if(!object)fail(404,'Arquivo indisponível.');return new Response(request.method==='HEAD'?null:object.body as any,{headers:{'Content-Type':asset!.mime_type,'Content-Disposition':`${asset!.mime_type.startsWith('image/')?'inline':'attachment'}; filename*=UTF-8''${encodeURIComponent(asset!.original_name)}`,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"sandbox; default-src 'none'"}});
}
