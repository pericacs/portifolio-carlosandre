import {all,auditStatement,body,decode,exec,fail,first,json,now,rate,stmt,uuid} from './core';
import {MODULES,moduleCheck,publicProject,validate} from './validation';
import type {Env,Row} from './types';
export async function entry(env:Env,module:string,id:string){moduleCheck(module);const row=await first(env,'SELECT * FROM cms_entries WHERE module=? AND id=? AND deleted_at IS NULL',module,id);if(!row)fail(404,'Conteúdo não encontrado.');return decode(row!);}
async function references(env:Env,id:string,module:string,data:Row,scope:string){
 const targets=new Set<string>(),media=new Map<string,boolean>();
 const addMedia=(value:string,document=false)=>{if(/^\/(images|documents)\/[\w.-]+$/.test(value))return;const match=/^\/api\/media\/([a-f0-9-]{36})$/.exec(value);if(!match)fail(422,'Use um arquivo enviado à biblioteca.');media.set(match![1],document||media.get(match![1])||false);};
 for(const f of MODULES[module].fields){const v=data[f.key];if(!v)continue;
  if(['reference','references'].includes(f.kind))for(const target of Array.isArray(v)?v:[v]){if(target===id||!await first(env,'SELECT id FROM cms_entries WHERE id=? AND module=? AND deleted_at IS NULL',target,f.module))fail(422,'Relacionamento inválido.');targets.add(target);}
  if(['media','gallery','document'].includes(f.kind))for(const value of Array.isArray(v)?v:[v])if(value)addMedia(value,f.kind==='document');
  if(f.kind==='smartmedia')for(const item of v)if(item.slot!=='video'&&item.url)addMedia(item.url);
  if(f.kind==='finaldemos')for(const item of v)if(item.image)addMedia(item.image);
  if(['richtext','finalrich','smartblocks','smartmedia'].includes(f.kind))for(const match of JSON.stringify(v).matchAll(/\/api\/media\/([a-f0-9-]{36})/g))media.set(match[1],media.get(match[1])||false);
 }
 for(const [key,document] of media){const asset=await first(env,'SELECT mime_type FROM media_assets WHERE id=? AND archived_at IS NULL',key);if(!asset||(document?!['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document'].includes(asset.mime_type):!asset.mime_type.startsWith('image/')))fail(422,'Arquivo incompatível ou inexistente.');}
 const statements=[stmt(env,'DELETE FROM cms_links WHERE entry_id=? AND scope=?',id,scope),stmt(env,'DELETE FROM cms_media_refs WHERE entry_id=? AND scope=?',id,scope)];
 for(const target of targets)statements.push(stmt(env,'INSERT INTO cms_links(id,entry_id,target_id,scope) VALUES(?,?,?,?)',uuid(),id,target,scope));
 for(const key of media.keys())statements.push(stmt(env,'INSERT INTO cms_media_refs(id,entry_id,media_id,scope) VALUES(?,?,?,?)',uuid(),id,key,scope));
 return statements;
}
export async function publicContent(env:Env){const modules:Record<string,Row[]>={};for(const name of Object.keys(MODULES))modules[name]=[];
 const rows=await all(env,'SELECT id,module,source_key,published_data,status,published_at,deleted_at FROM cms_entries');const legacyMap:Row={},hidden:string[]=[];
 for(const row of rows){if(row.source_key)legacyMap[row.source_key]=row.id;if(row.source_key&&(row.deleted_at||row.status==='archived'||(row.published_at&&!row.published_data)))hidden.push(row.source_key);if(row.published_data&&!row.deleted_at){const data=JSON.parse(row.published_data);modules[row.module]?.push({...row.module==='projetos'?publicProject(data):data,id:row.id,sourceKey:row.source_key});}}
 for(const values of Object.values(modules))values.sort((a,b)=>(a.sortOrder||0)-(b.sortOrder||0));return {initialized:!!await first(env,"SELECT id FROM site_settings WHERE key='cms_initialized'"),modules,legacyMap,hidden};}
const guard=(env:Env,sql:string,...args:any[])=>stmt(env,`INSERT INTO write_guards(id,valid) VALUES(?,CASE WHEN (${sql}) THEN 1 ELSE 0 END)`,uuid(),...args);
export async function save(env:Env,row:Row,data:Row,actor:string,action:string,version:number,extra:Row={},scope='draft'){
 if(!Number.isInteger(version)||row.version!==version)fail(409,'Conteúdo alterado. Recarregue antes de salvar.');
 const statements=[guard(env,'SELECT EXISTS(SELECT 1 FROM cms_entries WHERE id=? AND version=? AND deleted_at IS NULL)',row.id,version)];
 let draft=data;if(row.data._legacy)draft={...data,_legacy:row.data._legacy};
 const fields:Row={version:version+1,editor_id:actor,updated_at:now(),...extra};
 if(scope==='draft')Object.assign(fields,{data:JSON.stringify(draft),title:data.title,slug:data.slug||'main'});
 const refs=await references(env,row.id,row.module,data,scope);statements.push(...refs);
 if(action==='publish'){Object.assign(fields,{published_data:JSON.stringify(row.module==='projetos'?publicProject(draft):draft),published_at:now(),status:'published',scheduled_data:null,scheduled_at:null});}
 if(action!=='save'&&action!=='restore'){
  if(action==='publish')for(const table of ['cms_links','cms_media_refs'])statements.push(stmt(env,`DELETE FROM ${table} WHERE entry_id=? AND scope='scheduled'`,row.id));
  if(['archive','unpublish','cancel-schedule','delete'].includes(action))for(const table of ['cms_links','cms_media_refs'])statements.push(stmt(env,`DELETE FROM ${table} WHERE entry_id=? AND ${action==='delete'?'1=1':action==='cancel-schedule'?"scope='scheduled'":"scope IN ('published','scheduled')"}`,row.id));
 }
 const keys=Object.keys(fields);statements.push(stmt(env,`UPDATE cms_entries SET ${keys.map(k=>k+'=?').join(',')} WHERE id=?`,...keys.map(k=>fields[k]),row.id),stmt(env,'INSERT INTO cms_revisions(id,entry_id,editor_id,version,action,snapshot) VALUES(?,?,?,?,?,?)',uuid(),row.id,actor,version+1,action,JSON.stringify(scope==='draft'?draft:row.data)),auditStatement(env,'cms.'+action,actor,'cms_entries',row.id),stmt(env,'DELETE FROM write_guards'));
 if(action==='delete')statements.unshift(guard(env,'SELECT NOT EXISTS(SELECT 1 FROM cms_links WHERE target_id=?)',row.id));
 try{await env.DB.batch(statements);}catch{fail(409,'Conflito de versão, endereço ou relacionamento. Recarregue antes de salvar.');}
 return decode((await first(env,'SELECT * FROM cms_entries WHERE id=?',row.id))!);
}
export async function cms(request:Request,env:Env,path:string,user:Row){const parts=path.split('/').filter(Boolean),[module,id,action]=parts,u=new URL(request.url),method=request.method;
 if(path==='/schema'&&method==='GET')return json(MODULES);
 if(path==='/options'&&method==='GET')return json(await all(env,'SELECT id,module,title FROM cms_entries WHERE deleted_at IS NULL ORDER BY title LIMIT 3000'));
 moduleCheck(module);
 if(!id&&method==='GET'){const page=Math.max(1,Number(u.searchParams.get('page'))||1),limit=Math.min(100,Math.max(1,Number(u.searchParams.get('limit'))||12)),q=(u.searchParams.get('q')||'').slice(0,40),status=u.searchParams.get('status')||'';const where="module=? AND deleted_at IS NULL AND instr(lower(title),lower(?))>0 AND (?='' OR status=?)";return json({items:(await all(env,`SELECT * FROM cms_entries WHERE ${where} ORDER BY updated_at DESC LIMIT ? OFFSET ?`,module,q,status,status,limit,(page-1)*limit)).map(decode),total:(await first(env,`SELECT count(*) n FROM cms_entries WHERE ${where}`,module,q,status,status))!.n,page});}
 if(!id&&method==='POST'){
  await rate(env,'cms-write:'+user.admin_id,240);const data=validate(module,(await body(request)).data),key=uuid(),time=now();const statements=[stmt(env,'INSERT INTO cms_entries(id,module,slug,title,data,editor_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',key,module,data.slug||'main',data.title,JSON.stringify(data),user.admin_id,time,time),...await references(env,key,module,data,'draft'),stmt(env,'INSERT INTO cms_revisions(id,entry_id,editor_id,version,action,snapshot) VALUES(?,?,?,1,?,?)',uuid(),key,user.admin_id,'create',JSON.stringify(data)),auditStatement(env,'cms.create',user.admin_id,'cms_entries',key)];try{await env.DB.batch(statements);}catch{fail(409,'Endereço já cadastrado ou relacionamento inválido.');}return json(await entry(env,module,key),201);
 }
 const row=await entry(env,module,id);
 if(!action&&method==='GET')return json(row);
 if(action==='revisions'&&method==='GET')return json(await all(env,'SELECT version,action,created_at FROM cms_revisions WHERE entry_id=? ORDER BY version DESC',id));
 if(!action&&method==='PUT'){await rate(env,'cms-write:'+user.admin_id,240);const b=await body(request);return json(await save(env,row,validate(module,b.data),user.admin_id,'save',b.version));}
 if(action==='restore'&&method==='PUT'){const b=await body(request),revision=await first(env,'SELECT snapshot FROM cms_revisions WHERE entry_id=? AND version=?',id,b.revision);if(!revision)fail(404,'Versão não encontrada.');return json(await save(env,row,validate(module,JSON.parse(revision!.snapshot)),user.admin_id,'restore',b.version));}
 if(!action&&method==='DELETE'){if(MODULES[module].singleton)fail(409,'Módulo único.');await save(env,row,row.data,user.admin_id,'delete',Number(u.searchParams.get('version')),{deleted_at:now(),published_data:null,scheduled_data:null,scheduled_at:null,status:'archived'});return json({ok:true});}
 if(method==='POST'&&['publish','schedule','archive','unpublish','cancel-schedule'].includes(action)){
  const b=await body(request);if(action==='publish')return json(await save(env,row,validate(module,row.data,true),user.admin_id,action,b.version,{},'published'));
  if(action==='schedule'){if(typeof b.scheduledAt!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(b.scheduledAt)||Date.parse(b.scheduledAt)<=Date.now()||!Number.isFinite(Date.parse(b.scheduledAt)))fail(422,'Informe data futura com fuso.');const data=validate(module,row.data,true);return json(await save(env,row,data,user.admin_id,action,b.version,{status:'scheduled',scheduled_data:JSON.stringify({...data,...row.data._legacy?{_legacy:row.data._legacy}:{}}),scheduled_at:new Date(b.scheduledAt).toISOString()},'scheduled'));}
  return json(await save(env,row,row.data,user.admin_id,action,b.version,{scheduled_at:null,scheduled_data:null,status:action==='archive'?'archived':action==='cancel-schedule'&&row.published_data?'published':'draft',...action!=='cancel-schedule'?{published_data:null}:{}},'draft'));
 }
 fail(404,'Rota não encontrada.');
}
export async function dashboard(env:Env){const counts:Row={};for(const [name,module] of Object.entries({projects:'projetos',videos:'videos',experiences:'experiencias',draftArticles:'artigos'}))counts[name]=(await first(env,`SELECT count(*) n FROM cms_entries WHERE module=? AND deleted_at IS NULL ${name==='draftArticles'?"AND status='draft'":''}`,module))!.n;counts.publishedArticles=(await first(env,"SELECT count(*) n FROM cms_entries WHERE module='artigos' AND published_data IS NOT NULL AND deleted_at IS NULL AND coalesce(json_extract(published_data,'$.planned'),0)<>1"))!.n;counts.messages=(await first(env,"SELECT count(*) n FROM contact_messages WHERE status='new'"))!.n;counts.scheduled=(await first(env,"SELECT count(*) n FROM cms_entries WHERE status='scheduled' AND deleted_at IS NULL"))!.n;
 return {counts,recent:await all(env,'SELECT id,title,module type,updated_at FROM cms_entries WHERE deleted_at IS NULL ORDER BY updated_at DESC LIMIT 8'),scheduled:await all(env,"SELECT title,module type,scheduled_at FROM cms_entries WHERE status='scheduled' AND deleted_at IS NULL ORDER BY scheduled_at LIMIT 10"),activities:await all(env,'SELECT id,action,created_at FROM audit_logs ORDER BY created_at DESC LIMIT 8'),analyticsConnected:false,smtpConfigured:env.EMAIL_ENABLED==='true'};}
