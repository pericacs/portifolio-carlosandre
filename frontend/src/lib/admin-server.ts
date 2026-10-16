import 'server-only';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
export async function adminRequest(path:string){
  const token=(await cookies()).get('portfolio_session')?.value;
  if(!token)redirect('/admin/login');
  let response:Response;
  try{
    response=await fetch(`${process.env.API_INTERNAL_URL||'http://localhost:8000'}/api/admin${path}`,{
      headers:{Cookie:`portfolio_session=${encodeURIComponent(token)}`},cache:'no-store',signal:AbortSignal.timeout(8000)});
  }catch{throw Error('A administração está temporariamente indisponível. Tente novamente.');}
  if(response.status===401)redirect('/admin/login');
  if(!response.ok)throw Error('Não foi possível carregar a administração.');
  return response.json();
}
