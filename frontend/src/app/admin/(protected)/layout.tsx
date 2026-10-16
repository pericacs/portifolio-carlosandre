import {adminRequest} from '@/lib/admin-server';
import {AdminShell} from '@/components/admin/admin-shell';
export const dynamic='force-dynamic';
export default async function ProtectedLayout({children}:{children:React.ReactNode}){
  const user=await adminRequest('/auth/me');
  return <AdminShell email={user.email}>{children}</AdminShell>;
}
