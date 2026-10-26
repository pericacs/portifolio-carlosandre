// Mutations restricted to the disposable project created by verify-production.py.
const {execFileSync}=require('node:child_process'),assert=require('node:assert/strict');
const name=process.env.DOCX_TEST_BACKEND,worker=process.env.DOCX_TEST_WORKER;
assert(/^carlosandre-check-[a-f0-9]{10}-api$/.test(name||''));
const prefix=name.slice(0,-4);assert.equal(worker,prefix+'-worker');
const docker=(...args)=>execFileSync('docker',args,{encoding:'utf8',timeout:60000});
function expire(token,hard=false){
 assert(/^[A-Za-z0-9_-]{43}$/.test(token));
 docker('exec',name,'python','-c',`import json,time,hashlib; from app.docx_import import stage_root,write_manifest; p=stage_root()/hashlib.sha256('${token}'.encode()).hexdigest(); m=json.loads((p/'manifest.json').read_text()); m['expires']=time.time()-1; ${hard?"m['recover_until']=time.time()-1; ":''}write_manifest(p,m)`);
 // A second container/process sees the same volume and runs the real worker cleanup.
 docker('exec',worker,'python','-c','from sqlalchemy.orm import Session; from app.db import get_engine; from app.docx_import import cleanup_expired; db=Session(get_engine()); cleanup_expired(db); db.close()');
}
async function recreate(request,base){
 const info=JSON.parse(docker('inspect',name))[0],other=JSON.parse(docker('inspect',worker))[0];
 const volume=info.Mounts.find(x=>x.Destination==='/app/uploads');
 assert.equal(volume.Type,'volume');assert.equal(volume.Name,prefix+'-media');
 assert(other.Mounts.some(x=>x.Destination==='/app/uploads'&&x.Name===volume.Name));
 const env=info.Config.Env.flatMap(value=>['-e',value]);
 docker('rm','-f',name);
 docker('run','-d','--name',name,'--network',prefix,'--network-alias','backend','--security-opt','no-new-privileges:true','--memory','384m','--cpus','0.50',...env,'-v',volume.Name+':/app/uploads',info.Config.Image);
 for(let n=0;n<60;n++){
  try{if((await request.get(base+'/api/health/ready')).ok())return;}catch{}
  await new Promise(resolve=>setTimeout(resolve,500));
 }
 throw new Error('Disposable backend did not become ready after recreation');
}
module.exports={expire,recreate};
