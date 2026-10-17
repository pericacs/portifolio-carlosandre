import {createRemoteJWKSet, jwtVerify} from 'jose';
import type {Env,Row} from './types';
export class HttpError extends Error { constructor(public status:number,message:string){super(message);} }
export function fail(status:number,message:string):never{throw new HttpError(status,message);}
export const now=()=>new Date().toISOString();
export const uuid=()=>crypto.randomUUID();
export const json=(body:unknown,status=200,headers:HeadersInit={})=>Response.json(body,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...headers}});
export const stmt=(env:Env,sql:string,...args:any[])=>env.DB.prepare(sql).bind(...args);
export async function all(env:Env,sql:string,...args:any[]):Promise<Row[]>{return (await stmt(env,sql,...args).all<Row>()).results;}
export const first=(env:Env,sql:string,...args:any[])=>stmt(env,sql,...args).first<Row>();
export const exec=(env:Env,sql:string,...args:any[])=>stmt(env,sql,...args).run();
export function decode(row:Row):Row{const r={...row};for(const k of ['data','published_data','scheduled_data','snapshot','details','value'])if(typeof r[k]==='string'){try{r[k]=JSON.parse(r[k]);}catch{}}return r;}
export async function hash(value:string){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)))).map(x=>x.toString(16).padStart(2,'0')).join('');}
export function token(){return btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(32)))).replaceAll('+','-').replaceAll('/','_').replaceAll('=','');}
export function equal(a:string,b:string){let v=a.length^b.length;for(let i=0;i<Math.max(a.length,b.length);i++)v|=(a.charCodeAt(i)||0)^(b.charCodeAt(i)||0);return v===0;}
export function cookies(request:Request){return Object.fromEntries((request.headers.get('cookie')||'').split(';').map(x=>x.trim().split('=')) .filter(x=>x.length===2));}
export function cookie(env:Env,name:string,value:string,httpOnly=false,seconds=28800){return `${name}=${value}; Path=/; Max-Age=${seconds}; SameSite=Strict${env.SITE_URL.startsWith('https://')?'; Secure':''}${httpOnly?'; HttpOnly':''}`;}
export function origin(request:Request,env:Env){if(request.headers.get('origin')!==new URL(env.SITE_URL).origin)fail(403,'Origem inválida.');}
export function csrf(request:Request,env:Env){origin(request,env);const header=request.headers.get('x-csrf-token')||'',c=cookies(request).portfolio_csrf||'';if(!/^[A-Za-z0-9_-]{43}$/.test(header)||!equal(header,c))fail(403,'Token de segurança inválido.');return header;}
const keySets=new Map<string,ReturnType<typeof createRemoteJWKSet>>();
export async function access(request:Request,env:Env){
  if(env.ACCESS_REQUIRED==='false' && ['localhost','127.0.0.1'].includes(new URL(env.SITE_URL).hostname))return;
  if(!env.ACCESS_TEAM_DOMAIN||!env.ACCESS_AUD)fail(503,'Cloudflare Access ainda não configurado.');
  if(!/^[a-z0-9-]+\.cloudflareaccess\.com$/.test(env.ACCESS_TEAM_DOMAIN!))fail(503,'Configuração Access inválida.');
  const issuer=`https://${env.ACCESS_TEAM_DOMAIN}`;
  let keys=keySets.get(issuer);if(!keys){keys=createRemoteJWKSet(new URL(issuer+'/cdn-cgi/access/certs'));keySets.set(issuer,keys);}
  try{const {payload}=await jwtVerify(request.headers.get('cf-access-jwt-assertion')||'',keys,{issuer,audience:env.ACCESS_AUD,algorithms:['RS256']});return payload;}catch{fail(403,'Autenticação Cloudflare Access necessária.');}
}
export async function authenticated(request:Request,env:Env){
  await access(request,env);const t=cookies(request).portfolio_session||'';
  if(!/^[A-Za-z0-9_-]{43}$/.test(t))fail(401,'Entre no painel para continuar.');
  const session=await first(env,'SELECT s.*,u.email FROM admin_sessions s JOIN admin_users u ON u.id=s.admin_id WHERE s.token_hash=? AND s.revoked_at IS NULL AND s.expires_at>? AND u.active=1',await hash(t),now());
  if(!session)fail(401,'Sua sessão expirou.');
  if(!['GET','HEAD','OPTIONS'].includes(request.method)&&!equal(session!.csrf_hash,await hash(csrf(request,env))))fail(403,'Token de sessão inválido.');
  return session!;
}
export async function rate(env:Env,key:string,max:number){
  const time=now(),until=new Date(Date.now()+900000).toISOString();
  const result=await first(env,`INSERT INTO auth_rate_limits(key,attempts,expires_at) VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET attempts=CASE WHEN expires_at<=? THEN 1 ELSE attempts+1 END,expires_at=CASE WHEN expires_at<=? THEN excluded.expires_at ELSE expires_at END RETURNING attempts`,await hash(key),until,time,time);
  if(result!.attempts>max)fail(429,'Muitas tentativas. Aguarde 15 minutos.');
}
export const auditStatement=(env:Env,action:string,actor:string|null=null,entity:string|null=null,id:string|null=null)=>stmt(env,'INSERT INTO audit_logs(id,actor_id,action,entity_type,entity_id) VALUES(?,?,?,?,?)',uuid(),actor,action,entity,id);
export async function body(request:Request){const size=Number(request.headers.get('content-length')||0);if(size>1_000_000)fail(413,'Corpo muito grande.');const raw=await request.text();if(raw.length>1_000_000)fail(413,'Corpo muito grande.');try{return JSON.parse(raw);}catch{fail(422,'JSON inválido.');}}
export function text(value:unknown,min=0,max=1000){if(typeof value!=='string'||value.trim().length<min||value.length>max)fail(422,'Texto inválido.');return value.trim();}
export function email(value:unknown){const s=text(value,3,320).toLowerCase();if(!/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(s)||/[\r\n]/.test(s))fail(422,'E-mail inválido.');return s;}
export async function passwordHash(password:string,salt=crypto.getRandomValues(new Uint8Array(16))){const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(password),'PBKDF2',false,['deriveBits']);const bits=await crypto.subtle.deriveBits({name:'PBKDF2',salt:salt as BufferSource,iterations:100000,hash:'SHA-256'},key,256);return `pbkdf2-sha256$100000$${btoa(String.fromCharCode(...salt))}$${btoa(String.fromCharCode(...new Uint8Array(bits)))}`;}
export async function verifyPassword(password:string,encoded:string){const parts=encoded.split('$');if(parts[0]!=='pbkdf2-sha256'||parts[1]!=='100000')return false;try{return equal(encoded,await passwordHash(password,Uint8Array.from(atob(parts[2]),x=>x.charCodeAt(0))));}catch{return false;}}
