import {SmartFamilyPresentation} from '@/components/smartfamily/presentation';
import {notFound} from 'next/navigation';
import {adminRequest} from '@/lib/admin-server';
import {Workspace} from '@/components/cms/workspace';
import {Preview} from '@/components/cms/preview';
import {Messages} from '@/components/cms/messages';
import {MediaLibrary} from '@/components/cms/media-library';
import {DocxImport,ImportedArticlePreview} from '@/components/cms/docx-import';
export default async function ModulePage({params}:{params:Promise<{module:string;path?:string[]}>}){
 const {module,path=[]}=await params;
 await adminRequest('/auth/me');
 if(module==='mensagens')return <Messages/>;
 if(module==='midia')return <MediaLibrary/>;
 if(module==='artigos'&&path.length===1&&path[0]==='importar')return <DocxImport/>;
 const schemas=await adminRequest('/cms/schema');if(!schemas[module])notFound();
 if(path[1]==='preview'){const row=await adminRequest(`/cms/${module}/${path[0]}`);if(module==='artigos'&&row.data.docxImported)return <ImportedArticlePreview data={row.data}/>;if(module==='projetos'&&row.data.slug==='smartfamily'){const hidden=new Set([...(row.data.privateFields||[]),'privateNotes','_legacy']);const item=Object.fromEntries(Object.entries(row.data).filter(([k])=>!hidden.has(k)).map(([k,v]:[string,any])=>[k,k.startsWith('sf')&&Array.isArray(v)?v.filter(x=>typeof x!=='object'||x.visibility!=='PRIVADO'):v]));return <SmartFamilyPresentation item={item} preview/>;}return <Preview data={row.data} schema={schemas[module]}/>;}
 if(path.length>1)notFound();
 return <Workspace module={module} schema={schemas[module]} path={path}/>;
}
