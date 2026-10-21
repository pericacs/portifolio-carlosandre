'use client';
import {useEffect,useRef,useState} from 'react';
import {useRouter} from 'next/navigation';
import {api} from './api';
import {RichEditor} from './editor';
import {ArticleBody} from '@/components/articles/reading';
import {ArticleMeta} from '@/components/articles/card';
import article from '@/components/articles/articles.module.css';
import s from '@/app/admin/admin.module.css';
type Media={id:string;url:string;previewUrl:string;name:string;caption:string;sha256:string;width:number;height:number};
type Stage={token:string;data:Record<string,any>;warnings:string[];images:Media[];sections:number;suggestedSlug:string;collision:null|{id:string;title:string;version:number;status:string;canVersion:boolean};previousImport:null|{entry_id:string}};

export function DocxImportHistory({entryId}:{entryId:string}){
 const[rows,setRows]=useState<any[]>([]),[error,setError]=useState('');
 useEffect(()=>{api('/docx/history/'+entryId).then(setRows).catch(e=>setError(e.message));},[entryId]);
 return <section><h3>Importações do Word</h3>{error&&<p role="alert">{error}</p>}{rows.map((row,i)=><div className={s.orderRow} key={i}><span>{new Date(row.imported_at).toLocaleString('pt-BR')} · {row.sections} seções · {row.media_ids.length} imagens<br/><small>SHA-256 da origem: {row.source_sha256}</small>{row.warnings?.map((w:string)=><p key={w}>{w}</p>)}</span></div>)}{!rows.length&&!error&&<p>Nenhuma importação DOCX registrada.</p>}</section>;
}

export function ImportedArticlePreview({data}:{data:Record<string,any>}){
 return <article className={article.page}><header className={article.articleHeader}><ArticleMeta item={data}/><h1>{data.title}</h1>{data.subtitle&&<p className={article.summary}>{data.subtitle}</p>}<p className={article.summary}>{data.description}</p><div className={article.tags}>{(data.categories||[]).map((x:string)=><span key={x}>{x}</span>)}</div>{data.author&&<p className={article.byline}>Por {data.author}</p>}{data.cover&&<img className={article.cover} src={data.cover} alt={data.title}/>}</header><div className={article.reading}><ArticleBody html={data.body||''}/></div></article>;
}

export function DocxImport(){
 const router=useRouter(),pending=useRef(false),saved=useRef(false);
 const[result,setResult]=useState<any>(null),[recoveryToken,setRecoveryToken]=useState('');
 const[stage,setStage]=useState<Stage|null>(null),[data,setData]=useState<Record<string,any>>({}),[rendered,setRendered]=useState<Record<string,any>|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[reviewed,setReviewed]=useState(false),[decision,setDecision]=useState('auto');
 useEffect(()=>{if(!stage)return;const before=(event:BeforeUnloadEvent)=>{if(!saved.current)event.preventDefault();};window.addEventListener('beforeunload',before);return()=>window.removeEventListener('beforeunload',before);},[stage]);
 const temp=(image:Media)=>image.previewUrl+'?v='+image.sha256;
 function toPreview(value:string){for(const image of stage?.images||[])value=value.replaceAll(image.url,temp(image));return value;}
 function toStored(value:string){for(const image of stage?.images||[])value=value.replaceAll(temp(image),image.url);return value;}
 function change(key:string,value:any){setData(old=>({...old,[key]:value}));setRendered(null);setReviewed(false);}
 async function upload(file:File){if(file.size>8*1024*1024){setError('O DOCX deve ter até 8 MB (8.388.608 bytes).');return;}setBusy(true);setError('');try{const body=new FormData();body.append('file',file);const result=await api('/docx/preview','POST',body);saved.current=false;setResult(null);setStage(result);setData(result.data);setRendered(null);setDecision('auto');setReviewed(false);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 async function showPreview(){if(!stage)return;setBusy(true);setError('');try{const result=await api('/docx/staging/'+stage.token+'/render','POST',{data});const copy={...result.data,body:toPreview(result.data.body||''),cover:toPreview(result.data.cover||'')};setRendered(copy);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 function accepted(value:any){
  const id=value?.entryId||value?.entry?.id;
  if(typeof id!=='string'||!(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)))throw new Error('Resposta sem identificação do artigo. Consulte o resultado da importação.');
  saved.current=true;setResult({...value,entryId:id});setError('');
  if(value.entry?.status!=='archived')router.push('/admin/artigos/'+id+'?docx=saved');
 }
 async function recoverResult(token:string){const value=await api('/docx/staging/'+token+'/result');if(!value.entryId)throw new Error('Ainda não há confirmação de salvamento. Você pode tentar confirmar novamente, sem reenviar o documento.');accepted(value);}
 useEffect(()=>{const token=sessionStorage.getItem('docx-pending');if(token)setRecoveryToken(token);},[]);
 async function commit(){
  if(!stage||pending.current||saved.current)return;
  pending.current=true;setBusy(true);setError('');setRecoveryToken(stage.token);sessionStorage.setItem('docx-pending',stage.token);
  try{accepted(await api('/docx/staging/'+stage.token+'/commit','POST',{data,reviewed,decision,confirmCollision:decision!=='auto',targetId:decision==='version'?stage.collision?.id:null,version:decision==='version'?stage.collision?.version:null}));}
  catch(e){try{await recoverResult(stage.token);}catch{setError((e as Error).message+' Consulte o resultado antes de tentar novamente.');}}
  finally{pending.current=false;setBusy(false);}
 }
 async function recoverArchived(){const token=stage?.token||recoveryToken;if(!token||pending.current)return;pending.current=true;setBusy(true);try{const row=result?.entry||stage?.collision;accepted(await api('/docx/staging/'+token+'/recover','POST',{entryId:row.id,version:row.version}));}catch(e){setError((e as Error).message);}finally{pending.current=false;setBusy(false);}}
 function moveImage(image:Media,direction:number){const doc=new DOMParser().parseFromString(data.body||'','text/html'),element=doc.querySelector(`img[src="${image.url}"]`)?.closest('figure');if(!element)return;const neighbour=direction<0?element.previousElementSibling:element.nextElementSibling;if(!neighbour)return;if(direction<0)neighbour.before(element);else neighbour.after(element);change('body',doc.body.innerHTML);}
 function caption(image:Media,value:string){const doc=new DOMParser().parseFromString(data.body||'','text/html'),figure=doc.querySelector(`img[src="${image.url}"]`)?.closest('figure');if(figure){let label=figure.querySelector('figcaption');if(!label){label=doc.createElement('figcaption');figure.append(label);}label.textContent=value;figure.querySelector('img')?.setAttribute('alt',value);change('body',doc.body.innerHTML);}setStage(old=>old?{...old,images:old.images.map(x=>x.id===image.id?{...x,caption:value}:x)}:old);}
 return <><div className={s.pageHeading}><div><p className={s.eyebrow}>Artigos · Word</p><h1>Importar artigo do Word</h1><p>Extraia, revise e salve como rascunho. Nada é publicado automaticamente.</p></div><a className={s.secondary} href="/admin/artigos">Voltar aos artigos</a></div>
 {result&&<p className={s.success} role="status">{result.entry?.status==='archived'?'O artigo já existe e está arquivado.':'Artigo salvo. Abrindo o editor…'} <a href={'/admin/artigos/'+result.entryId+'?docx=saved'}>Abrir artigo existente</a></p>}
 {recoveryToken&&!result&&<p className={s.notice}><button type="button" className={s.secondary} disabled={busy} onClick={async()=>{try{await recoverResult(recoveryToken);}catch(e){setError((e as Error).message);}}}>Consultar resultado da importação</button></p>}
 {(result?.entry?.status==='archived'||stage?.collision?.status==='archived')&&<p className={s.notice}>O registro arquivado pode ser aberto ou recuperado sem duplicar conteúdo. <a href={'/admin/artigos/'+(result?.entryId||stage?.collision?.id)}>Abrir registro arquivado</a> <button type="button" className={s.secondary} disabled={busy} onClick={recoverArchived}>Recuperar como rascunho</button></p>}
 {error&&<p className={s.error} role="alert">{error}</p>}
 {!stage?<section className={s.panel}><div className={s.cmsForm}><label className={s.cmsField}>Documento DOCX<input type="file" accept=".docx" aria-label="Documento DOCX" disabled={busy} onChange={e=>{const f=e.target.files?.[0];if(f)upload(f);e.target.value='';}}/></label><p>{busy?'Validando estrutura e extraindo conteúdo…':'Até 8 MB, 32 imagens e 50 MB após descompressão. Macros e objetos ativos não são aceitos.'}</p><p>O arquivo original não será disponibilizado na biblioteca pública.</p></div></section>:<>
 <section className={s.notice}><strong>Revisão obrigatória</strong><p>{stage.sections} seções · {stage.images.length} imagens · {data.readingMinutes||1} min de leitura. A capa é apenas uma sugestão.</p><ul>{stage.warnings.map(x=><li key={x}>{x}</li>)}</ul></section>
 {stage.previousImport&&<p className={s.notice}>Este documento já foi importado. <a href={'/admin/artigos/'+stage.previousImport.entry_id}>Abrir artigo existente</a>. Repetir a confirmação padrão não cria duplicata.</p>}
 {stage.collision&&<section className={s.panel}><div className={s.cmsForm}><h2>Já existe um artigo com este slug</h2><p>{stage.collision.title}. A versão pública será preservada até uma publicação explícita.</p><label className={s.cmsField}>Decisão sobre a colisão<select aria-label="Decisão sobre a colisão" value={decision} onChange={e=>{setDecision(e.target.value);change('slug',e.target.value==='new'?stage.suggestedSlug:stage.data.slug);}}><option value="auto">Selecione ou abra o artigo já importado</option><option value="new">Confirmo criar novo artigo com outro slug</option>{stage.collision.canVersion&&<option value="version">Confirmo criar nova versão em rascunho (cancela agendamento)</option>}</select></label></div></section>}
 <section className={s.panel}><div className={s.cmsForm}>{[['title','Título'],['slug','Slug'],['subtitle','Subtítulo'],['author','Autor'],['publishedDate','Data editorial confirmada'],['category','Categoria'],['seoTitle','Título SEO']].map(([key,label])=><label className={s.cmsField} key={key}>{label}<input type={key==='publishedDate'?'date':'text'} value={data[key]||''} onChange={e=>change(key,e.target.value)}/>{!data[key]&&['author','category'].includes(key)&&<small>Revisão necessária; nenhum valor foi inventado.</small>}</label>)}
 <label className={s.cmsField}>Resumo editorial<textarea maxLength={1000} value={data.description||''} onChange={e=>change('description',e.target.value)}/></label><label className={s.cmsField}>Meta description<textarea value={data.metaDescription||''} onChange={e=>change('metaDescription',e.target.value)}/></label>
 {['categories','tags'].map(key=><label key={key} className={s.cmsField}>{key==='tags'?'Tags':'Assuntos'}<input value={(data[key]||[]).join(', ')} onChange={e=>change(key,e.target.value.split(',').map(x=>x.trim()).filter(Boolean))}/></label>)}
 <label className={s.cmsField}>Imagem de capa<select aria-label="Imagem de capa" value={data.cover||''} onChange={e=>change('cover',e.target.value)}><option value="">Sem capa</option>{stage.images.map((x,i)=><option key={x.id} value={x.url}>{i+1}. {x.caption||x.name}</option>)}</select></label>
 <div className={s.mediaGrid}>{stage.images.map((image,i)=><div key={image.id} className={s.mediaTile}><img src={temp(image)} alt={image.caption||'Imagem '+(i+1)}/><small>{image.width} × {image.height} · proporção original</small><label className={s.cmsField}>Legenda<textarea value={image.caption} onChange={e=>caption(image,e.target.value)}/></label><div className={s.cmsActions}><button type="button" className={s.secondary} onClick={()=>moveImage(image,-1)}>↑ Mover no corpo</button><button type="button" className={s.secondary} onClick={()=>moveImage(image,1)}>↓ Mover no corpo</button></div><label className={s.cmsField}>Substituir imagem<input type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={async e=>{const file=e.target.files?.[0];if(!file)return;setBusy(true);setError('');try{const body=new FormData();body.append('file',file);const response=await api(`/docx/staging/${stage.token}/media/${image.id}`,'PUT',body);setStage(old=>old?{...old,images:response.images.map((x:Media)=>({...x,caption:old.images.find(y=>y.id===x.id)?.caption||x.caption}))}:old);setRendered(null);setReviewed(false);}catch(e){setError((e as Error).message);}finally{setBusy(false);e.target.value='';}}}/></label></div>)}</div>
 <label className={s.cmsField}>Corpo completo em português<RichEditor label="Artigo importado" value={toPreview(data.body||'')} onChange={v=>change('body',toStored(v))} allowUpload={false}/></label></div></section>
 <div className={s.cmsActions}><button type="button" className={s.secondary} disabled={busy} onClick={showPreview}>Atualizar prévia da página pública</button><button type="button" className={s.secondary} disabled={busy} onClick={async()=>{try{await api('/docx/staging/'+stage.token,'DELETE');setStage(null);setRendered(null);}catch(e){setError((e as Error).message);}}}>Descartar importação</button></div>
 {rendered&&<section aria-label="Prévia da página pública" className={s.panel}><ImportedArticlePreview data={rendered}/></section>}
 <label className={s.checkField}><input type="checkbox" checked={reviewed} disabled={!rendered} onChange={e=>setReviewed(e.target.checked)}/>Revisei a prévia, o conteúdo, as legendas e a imagem de capa.</label><div className={s.cmsActions}><button type="button" className={s.primary} disabled={busy||!!result||!reviewed||!!stage.collision&&decision==='auto'&&!stage.previousImport} onClick={commit}>{busy?'Confirmando…':'Confirmar e salvar rascunho'}</button></div>
 </>}
 </>;
}
