"""Test Supabase signup and signin using values from frontend/.env.local.

Creates a unique test user and attempts to sign up and sign in.
"""
import os, sys, json, time
from urllib import request, error

env_path = os.path.join('frontend', '.env.local')
if not os.path.exists(env_path):
    print('missing env file', env_path)
    sys.exit(1)

env = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()

SUPABASE_URL = env.get('NEXT_PUBLIC_SUPABASE_URL')
ANON = env.get('NEXT_PUBLIC_SUPABASE_ANON_KEY')
if not SUPABASE_URL or not ANON:
    print('missing supabase config in', env_path)
    sys.exit(1)

email = f"autotest+{int(time.time())}@example.com"
password = 'Test1234!'

print('Signing up', email, 'at', SUPABASE_URL)

def post_json(url, obj):
    data = json.dumps(obj).encode('utf-8')
    req = request.Request(url, data=data, headers={'Content-Type':'application/json','apikey':ANON,'Authorization':'Bearer '+ANON})
    try:
        with request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode('utf-8')
    except error.HTTPError as e:
        return e.code, e.read().decode('utf-8')

signup_url = SUPABASE_URL.rstrip('/') + '/auth/v1/signup'
code, body = post_json(signup_url, {'email': email, 'password': password})
print('signup status', code)
print(body)

token_url = SUPABASE_URL.rstrip('/') + '/auth/v1/token?grant_type=password'
code2, body2 = post_json(token_url, {'email': email, 'password': password})
print('token status', code2)
print(body2)

if code2 == 200:
    try:
        obj = json.loads(body2)
        print('access_token present:', 'access_token' in obj)
    except Exception:
        pass
