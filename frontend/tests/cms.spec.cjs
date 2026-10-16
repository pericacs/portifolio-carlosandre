const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const sharp=require(process.env.SHARP_MODULE||'sharp');
const {execFileSync}=require('node:child_process');
const fs=require('node:fs/promises');
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const base='http://localhost:8080';
function python(code){return execFileSync('docker',['compose','exec','-T','backend','python','-c',code],{encoding:'utf8'});}
const fixture=JSON.parse(python(`import json,secrets
from app.db import get_engine
from app import admin,models as m
password=secrets.token_urlsafe(32)
email='cms-browser-'+secrets.token_hex(8)+'@example.com'
with get_engine().begin() as db:
 id=db.execute(m.admin_users.insert().values(email=email,password_hash=admin.hasher.hash(password)).returning(m.admin_users.c.id)).scalar_one()
print(json.dumps({'id':str(id),'email':email,'password':password}))`));
(async()=>{let browser;const report={screens:[],flows:[],visual:[]};
 try{
  browser=await chromium.launch();
  for(const width of [1440,390]){
   const context=await browser.newContext({viewport:{width,height:1000},deviceScaleFactor:1,reducedMotion:'reduce'});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
   await page.goto(base+'/admin/login');await page.locator('input[name=email]').fill(fixture.email);await page.locator('input[name=password]').fill(fixture.password);await page.getByRole('button',{name:'Entrar no painel'}).click();await page.waitForURL('**/admin');
   for(const module of ['','perfil','experiencias','formacoes','certificacoes','idiomas','curriculo','skills','categorias','projetos','cases','artigos','videos','midia','mensagens','configuracoes']){
    await page.goto(base+'/admin'+(module?'/'+module:''));
    await page.waitForLoadState('networkidle');
    assert.equal(await page.getByText('Conexão indisponível',{exact:true}).count(),0);
    assert.deepEqual(await page.locator('p[role=alert]').allTextContents(),[],module+' erro');
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),module+' overflow');
    const file=`docs/screenshots/cms/${module||'dashboard'}-${width}.png`;await page.screenshot({path:file,fullPage:true});report.screens.push(file);
    if(['experiencias','skills','projetos','cases','artigos','videos'].includes(module)){
     await page.getByRole('link',{name:'Editar',exact:true}).first().click();await page.waitForLoadState('networkidle');
     await page.screenshot({path:`docs/screenshots/cms/${module}-editor-${width}.png`,fullPage:true});
     if(module==='artigos'){await page.getByRole('button',{name:'Conteúdo',exact:true}).click();await page.screenshot({path:`docs/screenshots/cms/artigos-conteudo-${width}.png`,fullPage:true});}
    }
   }
   const smart=await context.request.get(base+'/api/admin/cms/projetos?q=SmartFamily').then(r=>r.json());
   await page.goto(base+'/admin/projetos/'+smart.items[0].id);await page.waitForLoadState('networkidle');
   for(const [index,name] of ['Informações gerais','Visão geral e solução','Imagens e mídia','Funcionalidades','Como funciona','Arquitetura e tecnologias','Links e acessos','Resultados e roadmap','SEO e publicação','Demonstrações','Perguntas frequentes'].entries()){
    await page.getByRole('button',{name,exact:true}).click();
    await page.screenshot({path:`docs/screenshots/cms/smartfamily-admin-${index+1}-${width}.png`,fullPage:true});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   }
   const smartPreview=await context.newPage();await smartPreview.goto(base+'/admin/projetos/'+smart.items[0].id+'/preview');await smartPreview.getByText('Pré-visualização autenticada · rascunho · somente campos públicos',{exact:true}).waitFor();assert.equal(await smartPreview.locator('#assistente').count(),1);await smartPreview.close();
   const publicPage=await browser.newPage({viewport:{width,height:1000}});
   await publicPage.goto(base+'/projetos/smartfamily');await publicPage.waitForLoadState('networkidle');
   await publicPage.locator('h1').waitFor();assert((await publicPage.locator('h1').innerText()).includes('Sua família organizada.'));
   assert.equal(await publicPage.locator('#assistente article').count(),8);
   assert.equal(await publicPage.getByText('Anotações privadas',{exact:false}).count(),0);
   await publicPage.screenshot({path:`docs/screenshots/cms/smartfamily-public-${width}.png`,fullPage:true});await publicPage.close();
   await page.goto(base+'/');await page.waitForLoadState('networkidle');await page.mouse.move(0,0);
   await page.screenshot({path:`docs/screenshots/cms/home-after-${width}.png`,fullPage:true});
   const contactTop=await page.locator('#contato').evaluate(e=>Math.floor(e.getBoundingClientRect().top+scrollY));
   const before=await sharp(`docs/screenshots/cms/home-before-${width}.png`).extract({left:0,top:0,width,height:contactTop}).raw().toBuffer();
   const after=await sharp(`docs/screenshots/cms/home-after-${width}.png`).extract({left:0,top:0,width,height:contactTop}).raw().toBuffer();
   let changed=0;for(let i=0;i<before.length;i++)if(before[i]!==after[i])changed++;
   assert.equal(contactTop,width===1440?2503:7323,"Posição da seção de contato alterada");
   assert(changed/before.length<0.0001,"Diferença visual relevante na Home");
   report.visual.push({width,contactTop,changedChannelsBeforeContact:changed});
   if(width===390){
    const key='qa-browser-'+crypto.randomBytes(4).toString('hex');
    await page.goto(base+'/admin/projetos/novo');await page.locator('#field-title').fill(key);await page.getByRole('button',{name:'Informações gerais',exact:true}).click();await page.locator('#field-description').fill('Projeto temporário criado pelo teste de interface.');
    await page.getByRole('button',{name:'Salvar rascunho',exact:true}).click();await page.getByRole('status').filter({hasText:'Rascunho salvo'}).waitFor();
    const csrf=await context.request.get(base+'/api/admin/auth/csrf').then(r=>r.json());
    const list=await context.request.get(base+'/api/admin/cms/projetos?q='+key).then(r=>r.json());const id=list.items[0].id;
    const anon=await browser.newContext();assert.equal((await anon.request.get(base+'/projetos/'+key)).status(),404);
    const preview=await context.newPage();await preview.goto(base+'/admin/projetos/'+id+'/preview');await preview.getByText('Pré-visualização autenticada.',{exact:false}).waitFor();await preview.close();
    await page.getByRole('button',{name:'Publicar',exact:true}).click();await page.getByRole('status').filter({hasText:'Publicado.'}).waitFor();
    assert.equal((await anon.request.get(base+'/projetos/'+key)).status(),200);
    await page.locator('#field-description').fill('Mudança ainda não publicada.');await page.getByRole('button',{name:'Salvar rascunho',exact:true}).click();await page.getByRole('status').filter({hasText:'Rascunho salvo'}).waitFor();
    assert(!(await anon.request.get(base+'/projetos/'+key).then(r=>r.text())).includes('Mudança ainda não publicada.'));
    await page.getByRole('button',{name:'Imagens e mídia',exact:true}).click();const png=await sharp({create:{width:80,height:50,channels:3,background:'#0664ff'}}).png().toBuffer();
    await page.locator('#field-cover').setInputFiles({name:'qa-image.png',mimeType:'image/png',buffer:png});await page.locator('img[alt="Imagem principal"]').waitFor();
    await page.getByRole('button',{name:'Salvar rascunho',exact:true}).click();await page.getByRole('status').filter({hasText:'Rascunho salvo'}).waitFor();
    await page.getByRole('button',{name:'SEO e publicação',exact:true}).click();await page.getByRole('button',{name:'Arquivar',exact:true}).click();await page.getByRole('status').filter({hasText:'Estado atualizado'}).waitFor();assert.equal((await anon.request.get(base+'/projetos/'+key)).status(),404);
    await page.getByRole('button',{name:'Excluir',exact:true}).click();await page.waitForURL('**/admin/projetos');report.flows.push('Projeto: criar, editar, rascunho privado, preview, publicar, preservar versão pública, upload, arquivar e excluir');
    await page.goto(base+'/admin/artigos/novo');await page.locator('#field-title').fill(key+'-artigo');await page.getByRole('button',{name:'Conteúdo',exact:true}).click();await page.getByRole('textbox',{name:'Artigo em português',exact:true}).fill('Texto de artigo criado no editor visual para verificação.');await page.getByRole('button',{name:'Publicar',exact:true}).click();await page.getByRole('status').filter({hasText:'Publicado.'}).waitFor();assert.equal((await anon.request.get(base+'/artigos/'+key+'-artigo')).status(),200);report.flows.push('Artigo: editor visual, salvar e publicar');
    const dashboard=await context.request.get(base+'/api/admin/dashboard').then(r=>r.json());
    if(!dashboard.smtpConfigured){
     await page.goto(base+'/#contato');await page.locator('[name=name]').fill('QA CMS');await page.locator('[name=email]').fill(fixture.email);await page.locator('[name=interest]').selectOption('Outro assunto');await page.locator('[name=message]').fill('Mensagem temporária enviada pelo teste de interface.');await page.locator('[name=consent]').check();
     // Human form completion can be faster under automation; respect the anti-spam minimum.
     await page.waitForTimeout(2100);await page.getByRole('button',{name:'Enviar mensagem',exact:true}).click();await page.getByRole('alert').filter({hasText:'indisponível'}).waitFor();assert.equal(await page.locator('[name=email]').inputValue(),fixture.email);report.flows.push('Contato sem SMTP: falha clara e dados preservados');
    }
    await anon.close();
   }
   assert.deepEqual(errors,[]);await context.close();
  }
  await fs.writeFile('docs/screenshots/cms/playwright-report.json',JSON.stringify(report,null,2));console.log(JSON.stringify({screens:report.screens.length,flows:report.flows,visual:report.visual}));
 }finally{
  if(browser)await browser.close();
  python(`from app.db import get_engine
from app import models as m,admin
from uuid import UUID
from pathlib import Path
import sqlalchemy as sa
uid=UUID('${fixture.id}')
with get_engine().begin() as db:
 ids=list(db.scalars(sa.select(m.cms_entries.c.id).where(m.cms_entries.c.editor_id==uid)))
 for t in [m.cms_links,m.cms_media_refs,m.cms_revisions]:db.execute(t.delete().where(t.c.entry_id.in_(ids)))
 db.execute(m.cms_entries.delete().where(m.cms_entries.c.id.in_(ids)))
 assets=list(db.execute(sa.select(m.media_assets.c.id,m.media_assets.c.storage_key).where(m.media_assets.c.uploaded_by==uid)))
 for aid,key in assets:
  db.execute(m.media_assets.delete().where(m.media_assets.c.id==aid))
  path=Path('/app/uploads')/key
  if path.parent==Path('/app/uploads'):path.unlink(missing_ok=True)
 mids=sa.select(m.contact_messages.c.id).where(m.contact_messages.c.email=='${fixture.email}')
 db.execute(m.contact_notifications.delete().where(m.contact_notifications.c.message_id.in_(mids)))
 db.execute(m.contact_messages.delete().where(m.contact_messages.c.email=='${fixture.email}'))
 db.execute(m.audit_logs.delete().where(m.audit_logs.c.actor_id==uid))
 db.execute(m.password_resets.delete().where(m.password_resets.c.admin_id==uid))
 db.execute(m.admin_sessions.delete().where(m.admin_sessions.c.admin_id==uid))
 db.execute(m.admin_users.delete().where(m.admin_users.c.id==uid))
 for key in ['login:account:${fixture.email}','cms-write:'+str(uid),'upload:'+str(uid),'contact-email:${fixture.email}']:
  db.execute(m.auth_rate_limits.delete().where(m.auth_rate_limits.c.key==admin.digest(key)))`);
 }
})().catch(e=>{console.error(e);process.exit(1)});
