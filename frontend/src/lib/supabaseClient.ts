import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.REACT_APP_SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.REACT_APP_SUPABASE_ANON_KEY!;

/**
 * Returns a Supabase client.
 *
 * Pass a Clerk session token (from `getToken({ template: 'supabase' })`) to
 * authenticate requests with row-level security once the Clerk → Supabase JWT
 * template is configured. Without a token the anon key is used — still safe
 * because queries are filtered by user_id in the application layer.
 */
export function getSupabaseClient(clerkToken?: string | null) {
  return createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    global: {
      headers: clerkToken
        ? { Authorization: `Bearer ${clerkToken}` }
        : {},
    },
  });
}
