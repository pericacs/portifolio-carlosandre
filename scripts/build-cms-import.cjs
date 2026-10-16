// Snapshot the approved local content without modifying it.
const fs=require('node:fs');const ts=require('../frontend/node_modules/typescript');
const curriculum=JSON.parse(fs.readFileSync('frontend/src/data/curriculum.json','utf8'));
const compiled=ts.transpileModule(fs.readFileSync('frontend/src/data/home.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
const home={};new Function('require','exports',compiled)(()=>({default:curriculum}),home);
const slug=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const records=[];
function add(module,key,data){records.push({module,source_key:`initial:${module}:${key}`,data});}
const common=(title,index=0)=>({title,slug:slug(title),visible:true,featured:true,sortOrder:index});
add('perfil','main',{title:'Carlos André',professionalTitle:'TECHNOLOGY & VENTURES',subtitle:'TECNOLOGIA · DADOS · IA · NEGÓCIOS',heroPrefix:'Da ideia ao ',heroHighlight:'impacto real.',heroDescription:'Transformo problemas complexos em produtos, plataformas\n e soluções de alto impacto, unindo tecnologia, dados e visão de negócio.',biographyPt:curriculum.about,biographyEn:[],objective:curriculum.objective,quote:'Construir tecnologia é, para mim, uma forma de servir pessoas.',signature:['Tecnologia','para um futuro','mais humano.'],metrics:[{value:'20+',label:'anos de experiência\nem tecnologia'},{value:'9B+',label:'registros processados\nno projeto CEF'},{value:'4',label:'projetos e iniciativas\napresentados'},{value:'∞',label:'novos desafios\na construir'}],photo:'/images/carlos-andre-executivo.png',email:'pericacs@gmail.com',whatsapp:'5548996277411'});
add('configuracoes','main',{title:'Carlos André | Technology & Ventures',footer:['Tecnologia hoje.','Um futuro melhor amanhã.'],services:home.services,sectionOrder:['projetos','consultoria','experiencia','competencias','artigos','videos'],retentionDays:180,locales:['pt-BR'],categories:['Tecnologia','Dados','IA','Negócios'],seoTitle:'Carlos André | Technology & Ventures',metaDescription:'Da ideia ao impacto real. Arquitetura de soluções, engenharia de dados, inteligência artificial e produtos digitais com Carlos André.'});
for(const [i,x] of curriculum.experiences.entries())add('experiencias',x.id,{...common(x.company,i),...x,title:x.company,slug:x.id,startMonth:x.startMonth||'',endMonth:x.endMonth||'',current:false,_legacy:x});
for(const [i,x] of curriculum.skills.entries()){
 const key=slug(x.title);add('categorias',key,{...common(x.title,i),icon:home.skills[i].icon,color:home.skills[i].color});
 for(const [j,item] of x.items.entries())add('skills',key+'-'+j,{...common(item,j),slug:key+'-'+slug(item)+'-'+j,categoryId:'SOURCE:initial:categorias:'+key});
}
add('formacoes','original',{...common(curriculum.education.degree),...curriculum.education});
curriculum.certifications.forEach((x,i)=>add('certificacoes','original-'+i,common(x,i)));
curriculum.languages.forEach((x,i)=>add('idiomas','original-'+i,common(x,i)));
add('curriculo','main',{title:'Currículo profissional — versão pública',file:curriculum.resume.publicDownload,privacyReviewed:true});
home.projects.forEach((x,i)=>add('projetos',slug(x.name),{...common(x.name,i),description:x.description,body:'<p>'+esc(x.detail)+'</p>',technologies:x.technologies,tags:x.tags,_legacy:x}));
curriculum.cases.forEach((x,i)=>add('cases',x.id,{...common(x.title,i),slug:x.id,company:x.company,description:x.summary,body:x.narrative.map(t=>'<p>'+esc(t)+'</p>').join(''),confidentialityReviewed:false,_legacy:x}));
home.articles.forEach((x,i)=>add('artigos',slug(x.title),{...common(x.title,i),description:x.description,tags:x.tags,planned:true,_legacy:x}));
home.videos.forEach((x,i)=>add('videos',slug(x.title),{...common(x.title,i),planned:true,_legacy:x}));
fs.writeFileSync('backend/app/data/cms_initial.json',JSON.stringify(records,null,2));console.log('Prepared',records.length,'records from existing sources.');

