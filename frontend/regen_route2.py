import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv(r'C:\Users\uniou\OneDrive - University of Brighton\Desktop\hackathon\backend\.env')
API_KEY = os.getenv('FANAR_API_KEY')

FRONTEND_DIR = r'C:\Users\uniou\OneDrive - University of Brighton\Desktop\hackathon\frontend'

prompt = 'MANDATORY: EMERALD GREEN and GOLD colors only. 3D sculpted decorative Islamic border frame. The frame border itself must be green and gold with carved geometric patterns. IMPORTANT: The background outside the frame and inside the frame must both be PURE BLACK #000000, NOT grey or light green. NO shadow, NO wall background, NO surface underneath — just pure black everywhere except the frame border itself. The frame ornaments are 3D sculpted green and gold Islamic geometric patterns. No text, no people, no shadows, no background objects.'

print("Generating frame_route.png...")
response = requests.post(
    'https://api.fanar.qa/v1/images/generations',
    headers={'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'},
    json={'model': 'Fanar-Oryx-IG-2', 'prompt': prompt, 'n': 1, 'size': '1024x1024'},
    timeout=90
)
data = response.json()
if 'data' in data:
    item = data['data'][0]
    if item.get('b64_json'):
        out_path = os.path.join(FRONTEND_DIR, 'frame_route.png')
        with open(out_path, 'wb') as f:
            f.write(base64.b64decode(item['b64_json']))
        print(f"Saved: {out_path}")
    elif item.get('url'):
        print(f"URL: {item['url']}")
    else:
        print(f"No image data: {list(item.keys())}")
else:
    print(f"Error: {data.get('error', data)}")
