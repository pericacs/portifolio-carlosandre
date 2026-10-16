// Real browser and PostgreSQL. Creates only an ephemeral administrator for this run.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const sharp=require(process.env.SHARP_MODULE||'sharp');
const {execFileSync}=require('node:child_process');
const fs=require('node:fs/promises');
const assert=require('node:assert/strict');
function python(code){return execFileSync('docker',['compose','exec','-T','backend','python','-c',code],{encoding:'utf8'});}
const setup=`import json,secrets
from app.db import get_engine
from app import admin,models as m
password=secrets.token_urlsafe(32)
email='browser-'+secrets.token_hex(8)+'@example.com'
with get_engine().begin() as db:
 id=db.execute(m.admin_users.insert().values(email=email,password_hash=admin.hasher.hash(password)).returning(m.admin_users.c.id)).scalar_one()
print(json.dumps({'id':str(id),'email':email,'password':password}))`;
(async()=>{
 const credentials=JSON.parse(python(setup));let browser;const report=[];
 try{
  browser=await chromium.launch({headless:true});
  for(const width of [1440,390]){
   const context=await browser.newContext({viewport:{width,height:1000},deviceScaleFactor:1,reducedMotion:'reduce'});
   const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
   assert.equal((await context.request.get('http://localhost:8080/api/admin/dashboard')).status(),401);
   await page.goto('http://localhost:8080/admin');await page.waitForURL('**/admin/login');
   await page.getByRole('button',{name:'Entrar no painel'}).waitFor();
   await page.screenshot({path:`docs/screenshots/admin/login-${width}.png`,fullPage:true});
   await page.locator('input[name=email]').fill(credentials.email);
   await page.locator('input[name=password]').fill(credentials.password);
   await page.getByRole('button',{name:'Entrar no painel'}).click();await page.waitForURL('**/admin');
   await page.getByRole('heading',{name:'Visão geral do portfólio'}).waitFor();
   const session=(await context.cookies()).find(c=>c.name==='portfolio_session');
   assert(session.httpOnly);assert.equal(session.sameSite,'Strict');
   assert.equal((await context.request.get('http://localhost:8080/api/admin/dashboard')).status(),200);
   assert.equal((await context.request.post('http://localhost:8080/api/admin/auth/logout')).status(),403);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:`docs/screenshots/admin/dashboard-${width}.png`,fullPage:true});
   if(width===390){await page.getByRole('button',{name:'Menu'}).click();await page.getByRole('link',{name:'Registro de operações'}).waitFor();await page.screenshot({path:'docs/screenshots/admin/menu-390.png',fullPage:true});}
   await page.getByRole('link',{name:'Registro de operações'}).click();await page.getByRole('heading',{name:'Registro de operações'}).waitFor();
   assert((await page.locator('tbody').innerText()).includes('auth.login'));
   await page.screenshot({path:`docs/screenshots/admin/auditoria-${width}.png`,fullPage:true});
   await page.goto('http://localhost:8080/admin/seguranca');await page.getByRole('heading',{name:'Acesso e segurança',exact:true}).waitFor();
   await page.getByRole('button',{name:'Sair',exact:true}).click();await page.waitForURL('**/admin/login');
   assert.equal((await context.request.get('http://localhost:8080/api/admin/auth/me')).status(),401);
   await page.goto('http://localhost:8080/admin/auditoria');await page.waitForURL('**/admin/login');
   if(width===1440){
    await page.goto('http://localhost:8080/admin/recuperar-senha');
    await page.getByText('O envio de e-mail ainda não está configurado.',{exact:false}).waitFor();
    const token=require('node:crypto').randomBytes(32).toString('base64url');
    python(`from app.db import get_engine
from app import models as m,admin
from datetime import timedelta
from uuid import UUID
with get_engine().begin() as db:
 db.execute(m.password_resets.insert().values(admin_id=UUID('${credentials.id}'),token_hash=admin.digest('${token}'),expires_at=admin.now()+timedelta(minutes=30)))`);
    await page.goto('http://localhost:8080/admin/redefinir-senha#token='+token);
    await page.locator('input[name=password]').fill(credentials.password);
    await page.locator('input[name=confirmation]').fill(credentials.password);
    await page.getByRole('button',{name:'Atualizar senha'}).click();
    await page.getByRole('status').filter({hasText:'Senha atualizada'}).waitFor();
    assert.equal(new URL(page.url()).hash,'');
   }
   await page.goto('http://localhost:8080/');await page.locator('.portrait img').evaluate(i=>i.decode());
   await page.mouse.move(0,0);
   const after=`docs/screenshots/admin/home-after-${width}.png`;
   await page.screenshot({path:after,fullPage:true});
   const before=await sharp(`docs/screenshots/admin/home-before-${width}.png`).raw().toBuffer({resolveWithObject:true});
   const current=await sharp(after).raw().toBuffer({resolveWithObject:true});
   assert.deepEqual(current.info,before.info);
   let changed=0;for(let i=0;i<before.data.length;i++)if(before.data[i]!==current.data[i])changed++;
   assert.equal(changed,0,'A Home sofreu alteração visual');assert.deepEqual(errors,[]);
   report.push({width,checks:'passed',homeChangedChannels:changed,javascriptErrors:errors});
   await context.close();
  }
  await fs.writeFile('docs/screenshots/admin/playwright-report.json',JSON.stringify(report,null,2));
  console.log(JSON.stringify(report));
 }finally{
  if(browser)await browser.close();
  python(`from app.db import get_engine
from app import models as m,admin
from uuid import UUID
id=UUID('${credentials.id}')
with get_engine().begin() as db:
 db.execute(m.audit_logs.delete().where(m.audit_logs.c.actor_id==id))
 db.execute(m.password_resets.delete().where(m.password_resets.c.admin_id==id))
 db.execute(m.admin_sessions.delete().where(m.admin_sessions.c.admin_id==id))
 db.execute(m.admin_users.delete().where(m.admin_users.c.id==id))
 db.execute(m.auth_rate_limits.delete().where(m.auth_rate_limits.c.key==admin.digest('login:account:${credentials.email}')))`);
 }
})().catch(e=>{console.error(e);process.exit(1)});
