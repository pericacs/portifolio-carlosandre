import {all,authenticated,decode,fail,HttpError,json} from './core';
import {auth} from './auth';
import {cms,dashboard,publicContent} from './cms';
import {contact,messages} from './contact';
import {media} from './media';
import type {Env} from './types';
export async function handleAPI(request:Request,env:Env){
 try{const path=new URL(request.url).pathname;
  if(request.method==='OPTIONS'){if(request.headers.get('origin')!==new URL(env.SITE_URL).origin)fail(403,'Origem inválida.');return new Response(null,{status:204,headers:{'Access-Control-Allow-Origin':new URL(env.SITE_URL).origin,'Access-Control-Allow-Credentials':'true','Access-Control-Allow-Methods':'GET,POST,PUT,PATCH,DELETE','Access-Control-Allow-Headers':'Content-Type,X-CSRF-Token','Vary':'Origin'}});}
  if(path==='/api/health/live'&&request.method==='GET')return json({status:'ok'});
  if(path==='/api/health/ready'&&request.method==='GET'){await env.DB.prepare('SELECT 1 FROM cms_entries LIMIT 1').first();return json({status:'ok',database:'connected',storage:'D1'});}
  if(path==='/api/content'&&request.method==='GET')return json(await publicContent(env));
  if(path.startsWith('/api/contact'))return await contact(request,env,path.slice('/api/contact'.length));
  if(path.startsWith('/api/media/'))return await media(request,env,path.slice('/api/media/'.length));
  if(path.startsWith('/api/admin/auth/'))return await auth(request,env,path.slice('/api/admin/auth'.length));
  if(path.startsWith('/api/admin/')){const user=await authenticated(request,env);
   if(path==='/api/admin/dashboard'&&request.method==='GET')return json(await dashboard(env));
   if(path==='/api/admin/audit'&&request.method==='GET')return json((await all(env,'SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 200')).map(decode));
   if(path==='/api/admin/cms/media'||path.startsWith('/api/admin/cms/media/'))return await media(request,env,path.slice('/api/admin/cms/media/'.length)||undefined,user);
   if(path==='/api/admin/messages'||path.startsWith('/api/admin/messages/'))return await messages(request,env,path.slice('/api/admin/messages'.length),user);
   if(path.startsWith('/api/admin/cms/'))return await cms(request,env,path.slice('/api/admin/cms'.length),user);
  }
  fail(404,'Rota não encontrada.');
 }catch(error){if(error instanceof HttpError)return json({detail:error.message},error.status);console.error('API operation failed; private details omitted');return json({detail:'Serviço temporariamente indisponível.'},503);}
}
