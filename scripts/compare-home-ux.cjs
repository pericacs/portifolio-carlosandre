// Compose real QA screenshots and the supplied reference; never alter product assets.
const sharp=require(process.env.SHARP_MODULE||'sharp'),fs=require('node:fs/promises'),path=require('node:path');
(async()=>{
 const root=path.resolve('docs/screenshots/home-ux-02'),out=path.join(root,'comparisons');await fs.mkdir(out,{recursive:true});
 async function pair(left,right,file,labels,width){
  const images=await Promise.all([left,right].map(p=>sharp(p).resize({width,withoutEnlargement:true}).png().toBuffer()));
  const metadata=await Promise.all(images.map(buffer=>sharp(buffer).metadata()));const panelWidth=Math.max(...metadata.map(x=>x.width)),height=Math.max(...metadata.map(x=>x.height));
  const label=Buffer.from(`<svg width="${panelWidth*2+16}" height="48"><rect width="100%" height="100%" fill="#07164e"/><g fill="white" font-family="Arial" font-size="20"><text x="16" y="32">${labels[0]}</text><text x="${panelWidth+32}" y="32">${labels[1]}</text></g></svg>`);
  await sharp({create:{width:panelWidth*2+16,height:height+48,channels:3,background:'#fff'}}).composite([{input:label,top:0,left:0},{input:images[0],top:48,left:0},{input:images[1],top:48,left:panelWidth+16}]).png({compressionLevel:9}).toFile(path.join(out,file));
 }
 for(const width of [1440,768,390])for(const page of ['home','hero','trajectory'])await pair(path.join(root,'before',page+'-'+width+'.png'),path.join(root,'after',page+'-'+width+'.png'),page+'-'+width+'.png',['Antes · '+width+'px','Depois · '+width+'px'],page==='home'?720:width);
 const reference='docs/references/home-ux-02-aprovado.png';
 const image=await sharp(reference).resize({width:1440}).png().toBuffer(),meta=await sharp(image).metadata();const current=await sharp(path.join(root,'after/home-1440.png')).extract({left:0,top:0,width:1440,height:meta.height}).png().toBuffer();
 const temp=path.resolve('.private/home-ux-02');await fs.writeFile(path.join(temp,'reference-1440.png'),image);await fs.writeFile(path.join(temp,'current-1440.png'),current);
 await pair(path.join(temp,'reference-1440.png'),path.join(temp,'current-1440.png'),'reference-desktop.png',['Referência aprovada · escala 1440px','Implementação · 1440px'],1440);
 console.log('Created 9 before/after comparisons and a reference/implementation comparison.');
})().catch(error=>{console.error(error);process.exit(1)});
