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
 const rows=[article('new-no-editorial-date','2026-10-25',999),article('o-split-do-mal','2026-10-19',999),article('engenharia-de-dados','2026-10-13',-100),article('oldest','2026-10-07',-999),article('fifth','2026-10-01',-9999)];
 rows[0].featured=false;rows[0].spotlight=true;
 const snapshot=JSON.stringify(rows),result=await read(rows);
 assert.deepEqual(result.articles,rows.slice(0,4));assert.deepEqual(result.modules.artigos,rows);assert.equal(JSON.stringify(rows),snapshot);
 // Preserve backend tie-breaking and missing-date placement; don't re-sort by
 // manual priority, slug or flags after SQL pagination/ordering.
 const tied=[article('zulu','2026-10-19'),article('alfa','2026-10-19'),article('unknown','')];
 assert.deepEqual((await read(tied)).articles,tied);
 assert.equal((await read([])).articles.length,0);
 const other=await read([rows[0]]);assert.deepEqual(result.projects,other.projects);assert.deepEqual(result.videos,other.videos);
 for(const item of result.articles)assert.deepEqual(item,rows.find(x=>x.id===item.id));
 console.log('PASS: Home is the first four API publications; fifth excluded; spotlight/non-featured included; no re-sort, mutation, duplicate fetch or other-module changes');
})().catch(error=>{console.error(error);process.exit(1)});
