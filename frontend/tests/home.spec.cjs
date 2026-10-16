const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
(async () => {
 const output = path.resolve(__dirname, '../../docs/screenshots');
 await fs.mkdir(output, { recursive:true });
 const browser = await chromium.launch({headless:true}); const report=[];
 try {
  for(const width of [1440,768,390]) {
   const context=await browser.newContext({viewport:{width,height:width===390?844:1000},deviceScaleFactor:1,reducedMotion:'reduce'});
   const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
   const response=await page.goto('http://localhost:8080/',{waitUntil:'networkidle'});assert.equal(response.status(),200);
   assert.match(await page.locator('h1').innerText(),/Da ideia ao\s+impacto real/);
   assert.equal(await page.getByText('A base para o próximo capítulo.').count(),0);
   assert.equal(await page.getByRole('heading',{level:2}).count(),7);
   await page.locator('.portrait img').evaluate(image=>image.decode());
   const layout=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,sections:[...document.querySelectorAll('main section')].map(s=>({id:s.id,top:s.getBoundingClientRect().top+scrollY,height:s.getBoundingClientRect().height}))}));
   assert.ok(layout.scrollWidth<=width,`Horizontal overflow at ${width}: ${layout.scrollWidth}`);
   assert.equal(await page.locator('.artwork').evaluateAll(items=>items.every(item=>{const [w,h]=item.style.aspectRatio.split('/').map(Number);const rect=item.getBoundingClientRect();return Math.abs(rect.width/rect.height-w/h)<.03;})),true,'Illustrations must preserve their aspect ratio');
   for(const id of ['projetos','consultoria','experiencia','competencias','artigos','videos','contato']) assert.ok(await page.locator(`#${id}`).isVisible());
   await page.screenshot({path:path.join(output,`home-${width}.png`),fullPage:true});
   if(width===1440)await page.screenshot({path:path.join(output,'home-desktop-top.png')});
   if(width===390){for(const id of ['inicio','projetos','experiencia','competencias','contato']) await page.locator(`#${id}`).screenshot({path:path.join(output,`mobile-${id}.png`)});await page.getByRole('button',{name:'Abrir menu'}).click();assert.equal(await page.locator('#main-nav').isVisible(),true);await page.locator('#main-nav').getByRole('link',{name:'Projetos',exact:true}).click();assert.equal(await page.locator('#main-nav').isVisible(),false);}
   const projectButton=page.getByRole('button',{name:'Conhecer SmartFamily',exact:true});await projectButton.click();assert.equal(await page.getByRole('dialog').isVisible(),true);assert.match(await page.getByRole('dialog').innerText(),/FastAPI/);await page.keyboard.press('Escape');assert.equal(await page.getByRole('dialog').count(),0);assert.equal(await projectButton.evaluate(element=>element===document.activeElement),true);
   await page.getByRole('button',{name:'Ver informações: Engenharia de Dados na prática',exact:true}).click();assert.match(await page.getByRole('dialog').innerText(),/ainda não está publicado/);await page.getByRole('button',{name:'Fechar detalhes'}).click();
   await page.locator('#formulario button[type=submit]').click();assert.equal(await page.locator('.form-result').count(),0);
   await page.locator('input[name=name]').fill('Teste de interface');await page.locator('input[name=email]').fill('interface@example.com');await page.locator('select[name=interest]').selectOption('Consultoria e arquitetura');await page.locator('textarea[name=message]').fill('Verificação local da interface. Nenhuma mensagem deve ser enviada.');await page.locator('input[name=consent]').check();await page.getByRole('button',{name:'Preparar mensagem'}).click();assert.match(await page.getByRole('status').innerText(),/Mensagem preparada/);assert.match(await page.getByRole('link',{name:'Abrir aplicativo de e-mail'}).getAttribute('href'),/^mailto:pericacs@gmail.com\?subject=/);
   for(const route of ['/experiencia','/sobre','/cases']) {
    const res=await page.goto(`http://localhost:8080${route}`,{waitUntil:'networkidle'});assert.equal(res.status(),200);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow ${route} at ${width}`);assert.equal(await page.locator('h1').count(),1);
    if(route==='/experiencia'){assert.equal(await page.locator('.timeline-item').count(),9);assert.match(await page.locator('#compass-cef').innerText(),/vínculo atual não confirmado/);await page.locator('#fastconnect summary').click();assert.match(await page.locator('#fastconnect details').innerText(),/Winker/);await page.locator('#fastconnect summary').click();}
    if(width!==768)await page.screenshot({path:path.join(output,`${route.slice(1)}-${width}.png`),fullPage:true});
   }
   const download=await context.request.get('http://localhost:8080/documents/carlos-andre-curriculo-publico.docx');assert.equal(download.status(),200);assert.equal((await download.body()).subarray(0,2).toString(),'PK');
   const health=await context.request.get('http://localhost:8080/api/health/ready');assert.equal(health.status(),200);assert.equal((await health.json()).database,'connected');
   assert.deepEqual(errors,[]);report.push({width,...layout,checks:'passed',javascriptErrors:errors});await context.close();
  }
  await fs.writeFile(path.join(output,'playwright-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({result:'passed',viewports:report.map(r=>({width:r.width,height:r.height})),screenshots:output},null,2));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
