from supabase import create_client
import os

SUPABASE_URL = "https://qktixcnagbbqggneebdq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFrdGl4Y25hZ2JicWdnbmVlYmRxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTg4MTU5MTgsImV4cCI6MjA3NDM5MTkxOH0.Bk_jpMdYCV4u0qP3F5uKhsIYmMtHzT0mA-_ukoj23BI"  # clé anon

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
