import {Children,isValidElement,ReactNode} from 'react';
export function OrderedSections({order,children}:{order:string[];children:ReactNode}){
 return <>{Children.toArray(children).sort((a,b)=>{
  const key=(x:ReactNode)=>isValidElement<{id?:string}>(x)?order.indexOf(x.props.id||''):-1;
  return key(a)-key(b);
 })}</>;
}
