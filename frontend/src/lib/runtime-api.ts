// Existing Docker/Next.js path stays intact.
export function apiFetch(path:string,init?:RequestInit){return fetch(`${process.env.API_INTERNAL_URL||'http://localhost:8000'}${path}`,init);}
