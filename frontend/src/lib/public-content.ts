import 'server-only';
import {cache} from 'react';
import initial from '@/data/cms-initial.json';
import originalCv from '@/data/curriculum.json';
import * as originalHome from '@/data/home';

// Approved static content is an immutable published baseline during migration.
// Drafts never reach this reader. Only explicit publication/withdrawal overrides it.
export const publicContent=cache(async()=>{
 let remote:any={modules:{},hidden:[],legacyMap:{}};
 try{const response=await fetch(`${process.env.API_INTERNAL_URL||'http://localhost:8000'}/api/content`,{cache:'no-store',signal:AbortSignal.timeout(5000)});if(response.ok)remote=await response.json();else if(response.status!==404)throw Error('Conteúdo indisponível');}catch(error){if(process.env.API_INTERNAL_URL)throw error;}
 const modules:Record<string,any[]>={};
 for(const item of initial as any[]){
  if(item.module==='artigos')continue; // Articles come exclusively from CMS publications; preserve legacy drafts in admin.
  modules[item.module]??=[];
  if(remote.hidden?.includes(item.source_key))continue;
  const data={...item.data,id:remote.legacyMap?.[item.source_key]||item.source_key,sourceKey:item.source_key};
  for(const key in data)if(typeof data[key]==='string'&&data[key].startsWith('SOURCE:'))data[key]=remote.legacyMap?.[data[key].slice(7)]||data[key].slice(7);
  modules[item.module].push(data);
 }
 for(const [module,rows] of Object.entries(remote.modules||{}) as [string,any[]][]){
  modules[module]??=[];
  for(const row of rows){const index=modules[module].findIndex(x=>x.sourceKey&&x.sourceKey===row.sourceKey);if(index>=0)modules[module][index]=row;else modules[module].push(row);}
 }
 for(const key in modules)modules[key]=modules[key].filter(x=>x.visible!==false).sort((a,b)=>(a.sortOrder||0)-(b.sortOrder||0));
 return modules;
});

export const publicData=cache(async()=>{
 const modules=await publicContent();
 const profile=modules.perfil?.[0]||{},settings=modules.configuracoes?.[0]||{};
 const period=(x:any)=>{
  const old=x._legacy;
  if(old&&(x.startMonth||'')===(old.startMonth||'')&&(x.endMonth||'')===(old.endMonth||'')&&!!x.endDateValidationRequired===!!old.endDateValidationRequired&&!x.current)return old.period;
  const format=(s:string)=>s?new Intl.DateTimeFormat('pt-BR',{month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(s+'-01T12:00:00Z')):'';
  return `${format(x.startMonth)}${x.current?' – Atual':x.endDateValidationRequired?' – término em validação':x.endMonth?' – '+format(x.endMonth):''}`;
 };
 const experiences=(modules.experiencias||[]).map(x=>({...x._legacy,...x,id:x._legacy?.id||x.id,period:period(x),wordmark:x._legacy?.wordmark||x.company,displayRole:x.displayRole||x.role,tags:x.tags||[],narrative:x.narrative||[],responsibilities:x.responsibilities||[],technologies:x.technologies||[],results:x.results||[]}));
 const skills=(modules.categorias||[]).map(x=>({...x,items:(modules.skills||[]).filter(v=>v.categoryId===x.id).map(v=>v.title)}));
 const cv={...originalCv,about:profile.biographyPt||[],objective:profile.objective||'',experiences,skills,education:modules.formacoes?.[0]||{degree:'',institution:'',period:''},certifications:(modules.certificacoes||[]).map(x=>x.title),languages:(modules.idiomas||[]).map(x=>x.title+(x.level?' · '+x.level:'')),resume:{...originalCv.resume,publicDownload:modules.curriculo?.[0]?.file||''},cases:(modules.cases||[]).map(x=>({...x._legacy,...x,summary:x.description,narrative:x._legacy?.narrative||[]}))} as typeof originalCv;
 const project=(x:any,i:number)=>(x.slug==='smartfamily'?{...originalHome.projects[0],slug:x.slug}:{...originalHome.projects[i%4],...x._legacy,...x,name:x.title,detail:x._legacy?.detail||x.description,technologies:x.technologies||[],tags:x.tags||[],crop:x._legacy?.crop||[45,271,192,67],imageAlt:x.title});
 const article=(x:any,i:number)=>({...originalHome.articles[i%3],...x._legacy,...x,tags:x.tags||[],crop:x._legacy?.crop||[46,853,257,53],imageAlt:x.title});
 const video=(x:any,i:number)=>({...originalHome.videos[i%4],...x._legacy,...x,crop:x._legacy?.crop||[70,853,170,53]});
 const contacts={email:settings.email||profile.email||'',whatsapp:settings.whatsapp||profile.whatsapp||'',linkedin:settings.linkedin||profile.linkedin||'',youtube:settings.youtube||profile.youtube||'',github:settings.github||profile.github||''};
 return {modules,profile,settings,contacts,curriculum:cv,projects:(modules.projetos||[]).filter(x=>x.featured).map(project) as (typeof originalHome.projects[number]&Record<string,any>)[],articles:(modules.artigos||[]).filter(x=>x.featured&&!x.planned).slice(0,3).map(article) as (typeof originalHome.articles[number]&Record<string,any>)[],videos:(modules.videos||[]).filter(x=>x.featured).map(video) as (typeof originalHome.videos[number]&Record<string,any>)[],experiences:experiences.filter(x=>x.featured),skills:skills.filter(x=>x.featured).map((x:any,i:number)=>({...originalHome.skills[i%7],...x,description:x.description||(modules.skills||[]).filter(v=>v.categoryId===x.id&&v.featured).map(v=>v.title).join(', ')+'.'})) as typeof originalHome.skills,services:settings.services||[]};
});
