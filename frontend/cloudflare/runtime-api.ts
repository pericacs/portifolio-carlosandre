import {env} from 'cloudflare:workers';
import {handleAPI} from './api';
import type {Env} from './types';
export function apiFetch(path:string,init?:RequestInit){return handleAPI(new Request(`${(env as unknown as Env).SITE_URL}${path}`,init),(env as unknown as Env));}
