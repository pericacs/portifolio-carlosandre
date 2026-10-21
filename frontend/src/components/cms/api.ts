export class ApiError extends Error {constructor(message:string,public status:number,public code=''){super(message);}}
async function readResponse(response:Response){
 if(response.status===401){window.location.assign('/admin/login');throw Error('Sessão expirada.');}
 if(response.status===413)throw Error('O servidor recusou o upload (HTTP 413). O limite do arquivo é 8 MB; se ele já está dentro desse limite, o proxy precisa ser revisado pelo administrador.');
 if(response.status===204&&response.ok)return null;
 const type=response.headers.get('content-type')||'';
 if(!/application\/(?:[\w.-]+\+)?json\b/i.test(type))throw Error(`O servidor retornou uma resposta inesperada (HTTP ${response.status}). Tente novamente; se persistir, contate o administrador.`);
 let data:any;try{data=await response.json();}catch{throw Error(`O servidor retornou uma resposta inválida (HTTP ${response.status}). Tente novamente.`);}
 if(!response.ok)throw new ApiError(typeof data?.detail==='string'?data.detail:typeof data?.detail?.message==='string'?data.detail.message:'Verifique os campos e tente novamente.',response.status,typeof data?.detail?.code==='string'?data.detail.code:'');
 return data;
}
export async function api(path:string,method='GET',body?:unknown){
 const headers:Record<string,string>={};
 if(method!=='GET'){
  const csrf=await readResponse(await fetch('/api/admin/auth/csrf',{cache:'no-store'}));
  if(typeof csrf?.csrfToken!=='string')throw Error('Não foi possível validar a sessão. Atualize a página e entre novamente.');
  headers['X-CSRF-Token']=csrf.csrfToken;
 }
 if(body&&!(body instanceof FormData))headers['Content-Type']='application/json';
 const response=await fetch('/api/admin'+path,{method,headers,body:body?(body instanceof FormData?body:JSON.stringify(body)):undefined,cache:'no-store'});
 return readResponse(response);
}
export type Field={key:string;label:string;kind:string;tab:string;required?:boolean;default?:unknown;options?:string[];module?:string;smartOnly?:boolean};
export type Schema={label:string;singleton?:boolean;tabs?:string[];fields:Field[]};
export type Entry={id:string;title:string;module:string;slug:string;data:Record<string,any>;version:number;status:string;published_data:Record<string,any>|null;scheduled_at:string|null;updated_at:string};
export const statusName:Record<string,string>={draft:'Rascunho',published:'Publicado',scheduled:'Agendado',archived:'Arquivado'};
