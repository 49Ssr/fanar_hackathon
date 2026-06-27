import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv(r'C:\Users\uniou\OneDrive - University of Brighton\Desktop\hackathon\backend\.env')
API_KEY = os.getenv('FANAR_API_KEY')

FRONTEND_DIR = r'C:\Users\uniou\OneDrive - University of Brighton\Desktop\hackathon\frontend'

prompt = 'MANDATORY: Generate this image in EMERALD GREEN and GOLD colors only. 3D sculpted decorative border frame, the ornaments must look three-dimensional and raised like carved stone or metal, NOT flat or line-drawn. Thick ornate 3D sculpted border on all four sides with depth and shadow. Islamic geometric patterns carved in 3D relief along the edges, compass rose medallions at corners that look raised and three-dimensional, arabesque vine carvings along the sides. Emerald green metallic surface with gold highlights on raised areas, dark green background. The center must be dark emerald green, NOT black. No text, no people. The border must look physically sculpted and three-dimensional like a carved decorative frame.'

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
