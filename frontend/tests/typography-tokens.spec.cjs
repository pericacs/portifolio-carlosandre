const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
function cssFiles(dir){return fs.readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?cssFiles(path.join(dir,e.name)):e.name.endsWith('.css')?[path.join(dir,e.name)]:[]);}
const globals=fs.readFileSync(path.resolve(__dirname,'../src/app/globals.css'),'utf8');
const all=cssFiles(path.resolve(__dirname,'../src')).map(p=>[p,fs.readFileSync(p,'utf8')]);
for(const [file,css] of all){
 for(const match of css.matchAll(/var\((--text-[\d]+)\)/g))assert(globals.includes(match[1]+':'),'undefined token '+match[1]+' in '+file);
 assert(!/font-size:\s*(?:[0-9]+(?:\.[0-9]+)?)px/.test(css),'isolated font size in '+file);
 assert(!/font:\s*(?:[0-9]+(?:\.[0-9]+)?)px/.test(css),'isolated shorthand font in '+file);
}
const luminance=hex=>hex.match(/../g).map(x=>parseInt(x,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
const pairs=[['435888','ffffff'],['075bce','ffffff'],['526482','fcfdff'],['465a76','f4f7fb'],['ffffff','075bce'],['244a73','edf3fb']];
const contrast=pairs.map(([fg,bg])=>{const a=luminance(fg),b=luminance(bg),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);assert(ratio>=4.5,fg+' on '+bg+' fails WCAG AA');return {fg,bg,ratio};});
console.log(JSON.stringify({result:'passed',tokens:'shared CSS scale, minimum 1rem',contrast},null,2));
