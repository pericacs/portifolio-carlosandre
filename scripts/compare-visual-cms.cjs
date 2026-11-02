// Evidence only: assemble real screenshots; never touches source article images.
const sharp=require(process.env.SHARP_MODULE||'sharp');
const fs=require('node:fs/promises'),path=require('node:path');
(async()=>{
 const root=path.resolve('docs/screenshots/visual-cms'),out=path.join(root,'comparisons');await fs.mkdir(out,{recursive:true});
 for(const width of [1440,768,390])for(const page of ['home','artigos','cms']){
  const height=width===390?1300:1000;
  const panels=[];
  for(const phase of ['before','after']){
   const file=path.join(root,phase,page+'-'+width+'.png'),meta=await sharp(file).metadata();
   const crop=await sharp(file).extract({left:0,top:0,width,height:Math.min(height,meta.height)}).extend({top:0,bottom:Math.max(0,height-meta.height),left:0,right:0,background:'white'}).png().toBuffer();panels.push(crop);
  }
  const label=Buffer.from(`<svg width="${width*2+16}" height="48"><rect width="100%" height="100%" fill="#07164e"/><g fill="white" font-family="Arial" font-size="22"><text x="16" y="32">Antes · ${page} · ${width}px</text><text x="${width+32}" y="32">Depois · ${page} · ${width}px</text></g></svg>`);
  await sharp({create:{width:width*2+16,height:height+48,channels:3,background:'#d9e4f5'}}).composite([{input:label,left:0,top:0},{input:panels[0],left:0,top:48},{input:panels[1],left:width+16,top:48}]).png({compressionLevel:9}).toFile(path.join(out,page+'-'+width+'.png'));
 }
 console.log('Created 9 before/after comparison sheets. Full-page originals retained.');
})().catch(e=>{console.error(e);process.exit(1)});
