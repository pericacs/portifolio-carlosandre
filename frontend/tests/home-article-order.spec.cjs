// Execute the real CMS reader: no server, private data or database writes.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const ts=require(process.env.TYPESCRIPT_MODULE||'typescript');
const source=fs.readFileSync(path.join(__dirname,'../src/lib/public-content.ts'),'utf8');
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,esModuleInterop:true}}).outputText;
async function read(rows){
 const exports={},calls=[];
 const modules={artigos:rows,projetos:[{id:'project',slug:'other',title:'Preserved project',featured:true}],videos:[{id:'video',title:'Preserved video',featured:true}]};
 const dependencies={'server-only':{},react:{cache:fn=>fn},'@/data/cms-initial.json':[],'@/data/curriculum.json':{resume:{}},'@/data/home':{projects:[{}],videos:[{}],skills:[]},'@/data/avallow.json':{}};
 vm.runInNewContext(compiled,{exports,require:key=>{assert(key in dependencies,key);return dependencies[key];},process:{env:{API_INTERNAL_URL:'http://cms.test'}},AbortSignal,fetch:async(url,options)=>{calls.push({url,cache:options.cache});return {ok:true,json:async()=>({modules})};}});
 const result=JSON.parse(JSON.stringify(await exports.publicData()));assert.deepEqual(calls,[{url:'http://cms.test/api/content',cache:'no-store'}]);return result;
}
const article=(slug,publishedDate,sortOrder=0)=>({id:slug,slug,title:slug,publishedDate,sortOrder,featured:true,visible:true,planned:false,cover:'/api/media/'+slug,description:'Preserved summary',tags:['Preserved'],categories:['CMS'],readingMode:'Interno',body:'<p>Preserved content.</p>'});
(async()=>{
 const oldest=article('split-payment-do-bem-e-do-mal','2026-10-07',-100),middle=article('engenharia-de-dados','2026-10-13',100),newest=article('o-split-do-mal','2026-10-19',999);
 oldest.created_at='2030-01-01';oldest.updated_at='2031-01-01';oldest.published_at='2032-01-01';newest.created_at='2020-01-01';newest.updated_at='2020-01-01';
 const input=[oldest,newest,middle],snapshot=JSON.stringify(input),result=await read(input);
 assert.deepEqual(result.articles.map(x=>x.slug),[newest.slug,middle.slug,oldest.slug]);assert.equal(JSON.stringify(input),snapshot);
 for(const item of result.articles)assert.deepEqual(item,input.find(x=>x.id===item.id));
 const tied=[article('zulu','2026-10-19',-500),article('alfa','2026-10-19',500)];
 for(const rows of [tied,[...tied].reverse()])assert.deepEqual((await read(rows)).articles.map(x=>x.slug),['alfa','zulu']);
 const undated=article('undated','',-10000),excluded=[{...article('not-featured','2030-01-01'),featured:false},{...article('hidden','2030-01-01'),visible:false},{...article('planned','2030-01-01'),planned:true}];
 assert.deepEqual((await read([undated,...excluded,newest])).articles.map(x=>x.slug),[newest.slug,'undated']);
 assert.equal((await read(Array.from({length:5},(_,i)=>article('article-'+i,'2026-10-'+String(i+1).padStart(2,'0'))))).articles.length,5);
 const other=await read([oldest]);assert.deepEqual(result.projects,other.projects);assert.deepEqual(result.videos,other.videos);
 // Home sorting must not reorder the listing's independently configured module.
 assert.deepEqual(result.modules.artigos.map(x=>x.slug),[oldest.slug,middle.slug,newest.slug]);
 console.log('PASS: CMS publication dates, expected chronology, deterministic ties, missing dates last, filters, all highlights, unchanged cards/other modules and no-store');
})().catch(error=>{console.error(error);process.exit(1)});
