import {access,authenticated,auditStatement,body,cookie,cookies,csrf,email,exec,first,hash,json,now,passwordHash,rate,stmt,text,token,uuid,verifyPassword,fail} from './core';
import type {Env} from './types';
export async function auth(request:Request,env:Env,path:string){
  await access(request,env);
  if(path==='/csrf'&&request.method==='GET'){const value=/^[A-Za-z0-9_-]{43}$/.test(cookies(request).portfolio_csrf||'')?cookies(request).portfolio_csrf:token();return json({csrfToken:value,passwordRecoveryAvailable:env.EMAIL_ENABLED==='true'},200,{'Set-Cookie':cookie(env,'portfolio_csrf',value)});}
  if(path==='/me'&&request.method==='GET'){const user=await authenticated(request,env);return json({email:user.email});}
  if(path==='/logout'&&request.method==='POST'){const user=await authenticated(request,env);await exec(env,'UPDATE admin_sessions SET revoked_at=? WHERE id=?',now(),user.id);const r=json({ok:true});r.headers.append('Set-Cookie',cookie(env,'portfolio_session','',true,0));r.headers.append('Set-Cookie',cookie(env,'portfolio_csrf','',false,0));return r;}
  if(request.method!=='POST')fail(404,'Rota não encontrada.');
  csrf(request,env);const data=await body(request);
  if(path==='/login'){
    const account=email(data.email),password=text(data.password,1,256);await rate(env,'login:peer:'+(request.headers.get('cf-connecting-ip')||'local'),30);await rate(env,'login:account:'+account,5);
    const user=await first(env,'SELECT * FROM admin_users WHERE email=? AND active=1',account);
    const valid=await verifyPassword(password,user?.password_hash||'pbkdf2-sha256$100000$AAAAAAAAAAAAAAAAAAAAAA==$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=');
    if(!user||!valid){await auditStatement(env,'auth.login_failed').run();fail(401,'E-mail ou senha inválidos.');}
    const t=token(),c=token(),time=now();
    await env.DB.batch([stmt(env,'UPDATE admin_sessions SET revoked_at=? WHERE token_hash=?',time,await hash(cookies(request).portfolio_session||'')),stmt(env,'INSERT INTO admin_sessions(id,admin_id,token_hash,csrf_hash,expires_at) VALUES(?,?,?,?,?)',uuid(),user.id,await hash(t),await hash(c),new Date(Date.now()+8*3600000).toISOString()),auditStatement(env,'auth.login',user.id)]);
    const response=json({email:user.email});response.headers.append('Set-Cookie',cookie(env,'portfolio_session',t,true));response.headers.append('Set-Cookie',cookie(env,'portfolio_csrf',c));return response;
  }
  if(path==='/recovery'){
    const account=email(data.email);await rate(env,'recovery:'+account,3);
    if(env.EMAIL_ENABLED!=='true'||!env.EMAIL_FROM)fail(503,'Recuperação por e-mail indisponível.');
    const user=await first(env,'SELECT id,email FROM admin_users WHERE email=? AND active=1',account);
    if(user){const t=token(),id=uuid();await exec(env,'INSERT INTO password_resets(id,admin_id,token_hash,expires_at) VALUES(?,?,?,?)',id,user.id,await hash(t),new Date(Date.now()+1800000).toISOString());try{await env.EMAIL.send({from:env.EMAIL_FROM,to:user.email,subject:'Redefinir acesso ao portfólio',text:`Redefina em até 30 minutos: ${env.SITE_URL}/admin/redefinir-senha#token=${t}`});}catch{await exec(env,'UPDATE password_resets SET used_at=? WHERE id=?',now(),id);}}
    return json({message:'Se o e-mail estiver cadastrado, você receberá as instruções.'},202);
  }
  if(path==='/reset'){
    const t=text(data.token,43,43),password=text(data.password,14,256),time=now(),encoded=await passwordHash(password);
    const reset=await first(env,'SELECT * FROM password_resets WHERE token_hash=? AND used_at IS NULL AND expires_at>?',await hash(t),time);if(!reset)fail(422,'Link inválido ou expirado.');
    // Consume conditionally and guard every dependent statement with the same claim marker.
    const claim=uuid();await env.DB.batch([stmt(env,'UPDATE password_resets SET used_at=? WHERE id=? AND used_at IS NULL AND expires_at>?',claim,reset!.id,time),stmt(env,'UPDATE admin_users SET password_hash=? WHERE id=? AND EXISTS(SELECT 1 FROM password_resets WHERE id=? AND used_at=?)',encoded,reset!.admin_id,reset!.id,claim),stmt(env,'UPDATE admin_sessions SET revoked_at=? WHERE admin_id=? AND EXISTS(SELECT 1 FROM password_resets WHERE id=? AND used_at=?)',time,reset!.admin_id,reset!.id,claim)]);return json({ok:true});
  }
  fail(404,'Rota não encontrada.');
}
