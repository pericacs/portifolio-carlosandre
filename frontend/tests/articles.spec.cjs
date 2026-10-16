const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
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
(async()=>{let browser;
 try{
 browser=await chromium.launch();
 const source=JSON.parse(await fs.readFile('backend/app/data/articles/content.json','utf8')).filter(x=>x.contentType==='Artigo');
 const request=await browser.newContext();const published=(await (await request.request.get(base+'/api/content')).json()).modules.artigos;
 assert.equal(published.length,2);assert.equal(published.filter(x=>x.readingMode==='Interno').length,2);
 for(const x of source){const live=published.find(v=>v.slug===x.slug);assert(live);assert.equal(live.originalUrl,x.originalUrl);assert.equal(live.publishedDate,x.publishedDate);if(x.readingMode==='Interno'){assert(live.body.includes('figcaption'));assert(live.body.length>15000);}}
 const media=new Set(published.flatMap(x=>[x.cover,...[...x.body.matchAll(/src="([^"]+)"/g)].map(m=>m[1])]).filter(Boolean));assert.equal(media.size,17);for(const url of media)assert.equal((await request.request.get(base+url)).status(),200);await request.close();
 for(const width of [1440,820,390]){
 const context=await browser.newContext({viewport:{width,height:1000},permissions:['clipboard-read','clipboard-write']});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/');assert.equal(await page.locator('#artigos article').count(),2);assert.equal(await page.locator('#artigos').getByText('Em preparação',{exact:false}).count(),0);await page.getByRole('link',{name:'Ver todos os artigos',exact:true}).click();await page.waitForURL('**/artigos');assert.equal(await page.locator('main article').count(),2);assert.equal(await page.getByRole('heading',{name:source[0].title,exact:true}).count(),1);
 for(const [label,count] of [['Engenharia de Dados',1],['IA',1],['Payments',2],['Segurança',0],['Todos',2]]){await page.getByRole('button',{name:label,exact:true}).click();assert.equal(await page.locator('main article').count(),count);}
 await page.getByLabel('Buscar por título ou resumo').fill('calendário');assert.equal(await page.locator('main article').count(),1);await page.getByLabel('Buscar por título ou resumo').fill('sem-resultado-xyz');assert.equal(await page.locator('main article').count(),0);await page.getByLabel('Buscar por título ou resumo').fill('');
 assert.equal(await page.locator('main time').count(),2);for(const x of source.filter(x=>x.contentType==='Insight'))assert(await page.locator('main a').evaluateAll((as,url)=>as.some(a=>a.getAttribute('href')===url),x.originalUrl));
 await page.locator('main img').evaluateAll(async imgs=>{for(const img of imgs){img.loading='eager';await img.decode();}});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:`docs/screenshots/cms/articles-list-${width}.png`,fullPage:true});
 for(const x of source.slice(0,2)){assert.equal((await page.goto(base+'/artigos/'+x.slug)).status(),200);await page.reload();await page.getByRole('heading',{level:1,name:x.title,exact:true}).waitFor();await page.locator('article img').evaluateAll(async imgs=>{for(const img of imgs){img.loading='eager';await img.decode();}});const zoom=page.getByRole('button',{name:'Ampliar imagem: Conteúdo do artigo',exact:true}).first();await zoom.click();await page.getByRole('dialog',{name:'Imagem ampliada do artigo'}).waitFor();await page.keyboard.press('Escape');await page.getByText('Neste artigo',{exact:true}).click();assert(await page.getByRole('navigation',{name:'Sumário do artigo'}).getByRole('link').count()>0);if(x.slug===source[0].slug){await page.getByRole('button',{name:'Copiar código',exact:true}).first().click();assert((await page.evaluate(()=>navigator.clipboard.readText())).includes('def moeda'));await page.screenshot({path:`docs/screenshots/cms/article-reading-${width}.png`,fullPage:true});}assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
 assert.deepEqual(errors,[]);await context.close();console.log(width+': listing, filters, search, images, zoom, code copy, direct URLs and reload passed');
 }
 const page=await browser.newPage();await page.goto(base+'/admin/login');await page.locator('input[name=email]').fill(fixture.email);await page.locator('input[name=password]').fill(fixture.password);await page.getByRole('button',{name:'Entrar no painel'}).click();await page.waitForURL('**/admin');
 await page.goto(base+'/admin/artigos/novo');await page.locator('#field-title').fill('QA artigo '+fixture.id);const slug='qa-artigo-'+fixture.id;await page.locator('#field-slug').fill(slug);await page.locator('#field-contentType').selectOption('Artigo');await page.locator('#field-readingMode').selectOption('Interno');await page.locator('#field-author').fill('Autor de teste');await page.getByRole('button',{name:'Conteúdo',exact:true}).click();await page.locator('#field-description').fill('Resumo inicial do teste de persistência.');await page.locator('#field-categories').fill('Engenharia de Dados\nIA');await page.getByRole('textbox',{name:'Artigo em português',exact:true}).fill('Conteúdo de teste para verificar persistência administrativa.');await page.getByRole('button',{name:'Salvar rascunho',exact:true}).click();await page.getByRole('status').filter({hasText:'Rascunho salvo'}).waitFor();
 const entries=await page.evaluate(async()=>{const r=await fetch('/api/admin/cms/artigos?limit=100');return r.json();});const test=entries.items.find(x=>x.slug===slug);assert(test);await page.goto(base+'/admin/artigos/'+test.id);await page.getByRole('button',{name:'Conteúdo',exact:true}).click();assert.equal(await page.locator('#field-description').inputValue(),'Resumo inicial do teste de persistência.');await page.getByRole('button',{name:'Publicar',exact:true}).click();await page.getByRole('status').filter({hasText:'Publicado.'}).waitFor();
 const anon=await browser.newPage();assert.equal((await anon.goto(base+'/artigos/'+slug)).status(),200);await page.locator('#field-description').fill('Resumo revisado e persistido.');await page.getByRole('button',{name:'Salvar rascunho',exact:true}).click();await page.getByRole('status').filter({hasText:'Rascunho salvo'}).waitFor();await anon.reload();assert.equal(await anon.getByText('Resumo inicial do teste de persistência.',{exact:true}).count(),1);await page.reload();await page.getByRole('button',{name:'Conteúdo',exact:true}).click();assert.equal(await page.locator('#field-description').inputValue(),'Resumo revisado e persistido.');await page.getByRole('button',{name:'Publicar',exact:true}).click();await page.getByRole('status').filter({hasText:'Publicado.'}).waitFor();await anon.reload();assert.equal(await anon.getByText('Resumo revisado e persistido.',{exact:true}).count(),1);await anon.close();
 await page.goto(base+'/admin/artigos/'+published[0].id);await page.screenshot({path:'docs/screenshots/cms/articles-admin.png',fullPage:true});console.log('CMS create, reload, edit, draft isolation and publication persistence passed');
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
