export async function api(path:string,method='GET',body?:unknown){
 const headers:Record<string,string>={};
 if(method!=='GET'){
  const csrf=await fetch('/api/admin/auth/csrf',{cache:'no-store'}).then(r=>r.json());headers['X-CSRF-Token']=csrf.csrfToken;
 }
 if(body&&!(body instanceof FormData))headers['Content-Type']='application/json';
 const response=await fetch('/api/admin'+path,{method,headers,body:body?(body instanceof FormData?body:JSON.stringify(body)):undefined,cache:'no-store'});
 if(response.status===401){window.location.assign('/admin/login');throw Error('Sessão expirada.');}
 const data=await response.json();if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Verifique os campos e tente novamente.');return data;
}
export type Field={key:string;label:string;kind:string;tab:string;required?:boolean;default?:unknown;options?:string[];module?:string;smartOnly?:boolean};
export type Schema={label:string;singleton?:boolean;tabs?:string[];fields:Field[]};
export type Entry={id:string;title:string;module:string;slug:string;data:Record<string,any>;version:number;status:string;published_data:Record<string,any>|null;scheduled_at:string|null;updated_at:string};
export const statusName:Record<string,string>={draft:'Rascunho',published:'Publicado',scheduled:'Agendado',archived:'Arquivado'};
