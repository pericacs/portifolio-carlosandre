import next from 'vinext/server/fetch-handler';
import type {ExecutionContext,ScheduledController} from '@cloudflare/workers-types';
import {access,HttpError,json,all,decode} from './core';
import {handleAPI} from './api';
import {save} from './cms';
import {deliver} from './contact';
import {validate} from './validation';
import type {Env} from './types';
export default {
 async fetch(request:Request,env:Env,ctx:ExecutionContext){
  const path=new URL(request.url).pathname;
  if(path.startsWith('/api/'))return handleAPI(request,env);
  if(path==='/admin'||path.startsWith('/admin/')){try{await access(request,env);}catch(e){return json({detail:e instanceof Error?e.message:'Acesso necessário'},e instanceof HttpError?e.status:403);}}
  if(/^\/(images|documents)\//.test(path)){
   // Only the public/ tree reviewed in Git is copied to this prefix. Private uploads have no route here.
   const object=await env.MEDIA.get('public'+path);if(object){const headers=new Headers();object.writeHttpMetadata(headers);headers.set('X-Content-Type-Options','nosniff');headers.set('Cache-Control','public, max-age=3600');if(path.startsWith('/documents/'))headers.set('Content-Disposition',`attachment; filename*=UTF-8''${encodeURIComponent(path.split('/').pop()!)}`);return new Response(request.method==='HEAD'?null:object.body as any,{headers});}
  }
  const response=await next.fetch(request,env,ctx);const headers=new Headers(response.headers);headers.set('X-Content-Type-Options','nosniff');headers.set('Referrer-Policy','strict-origin-when-cross-origin');headers.set('X-Frame-Options','DENY');if(path.startsWith('/admin')){headers.set('Cache-Control','no-store');headers.set('X-Robots-Tag','noindex, nofollow');}return new Response(response.body,{status:response.status,headers});
 },
 async scheduled(_event:ScheduledController,env:Env,ctx:ExecutionContext){
  ctx.waitUntil((async()=>{
   const rows=await all(env,"SELECT * FROM cms_entries WHERE status='scheduled' AND scheduled_at<=? AND deleted_at IS NULL LIMIT 10",new Date().toISOString());
   for(const raw of rows){const row=decode(raw);try{await save(env,row,validate(row.module,row.scheduled_data,true),row.editor_id,'publish',row.version,{},'published');}catch{console.error('Scheduled publication failed; content preserved');}}
   for(const job of await all(env,'SELECT message_id FROM contact_notifications WHERE sent_at IS NULL AND attempts<5 AND next_attempt_at<=? LIMIT 10',new Date().toISOString()))await deliver(env,job.message_id);
  })());
 }
};
