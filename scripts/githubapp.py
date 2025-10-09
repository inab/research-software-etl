import jwt
import time
import requests

# Create JWT
app_id = '983619'
private_key = open('scripts/metadata-updater-for-fairsoft.2024-08-30.private-key.pem').read()
payload = {
    'iat': int(time.time()),
    'exp': int(time.time()) + 600,
    'iss': app_id
}
jwt_token = jwt.encode(payload, private_key, algorithm='RS256')

# Get installations
headers = {
    'Authorization': f'Bearer {jwt_token}',
    'Accept': 'application/vnd.github+json'
}
r = requests.get('https://api.github.com/app/installations', headers=headers)
installations = r.json()

# Count installations and optionally repositories
print(f"Total installations: {len(installations)}")