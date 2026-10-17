import type {D1Database,R2Bucket,Fetcher} from '@cloudflare/workers-types';
export interface Env {
  DB: D1Database;
  MEDIA: R2Bucket;
  ASSETS?: Fetcher;
  SITE_URL: string;
  ACCESS_REQUIRED: string;
  ACCESS_TEAM_DOMAIN?: string;
  ACCESS_AUD?: string;
  EMAIL_ENABLED?: string;
  EMAIL_FROM?: string;
  EMAIL: {send(message:{to:string;from:string;subject:string;text:string;replyTo?:string}):Promise<{messageId:string}>};
}
export type Row = Record<string, any>;
