// public/js/supabaseClient.js
import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm";

export const SUPABASE_URL = "https://vlojyucqsnkpxvvigieu.supabase.co";
export const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZsb2p5dWNxc25rcHh2dmlnaWV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk2ODEwOTgsImV4cCI6MjA4NTI1NzA5OH0.Syw3cQSkxDSZ0j8XVsRM-iI7vXy2QQ1VCCTtPvorY_0";

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
