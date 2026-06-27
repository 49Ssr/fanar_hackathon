import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv(r'C:\Users\uniou\OneDrive - University of Brighton\Desktop\hackathon\backend\.env')
API_KEY = os.getenv('FANAR_API_KEY')

FRONTEND_DIR = r'C:\Users\uniou\OneDrive - University of Brighton\Desktop\hackathon\frontend'

images = [
    {
        'filename': 'frame_event.png',
        'prompt': 'MANDATORY: Generate this image in GOLD and BLACK colors only. The decorative border frame ornaments MUST be gold colored (#c9a84c), NOT white or grey. Arabic decorative border frame, 8-pointed Islamic geometric stars on top and bottom edges, arabesque floral vines on left and right sides, 12-pointed star medallions at all four corners, rich gold color on pure black background, empty black center, picture frame style, no text, no people. IMPORTANT: center must be completely empty black. Only gold colored decorations on the border edges and corners.'
    },
    {
        'filename': 'frame_schedule.png',
        'prompt': 'MANDATORY: Generate this image in DEEP BLUE and SILVER colors only. The decorative border frame ornaments MUST be blue and silver colored, NOT white or grey. Arabic decorative border frame, mashrabiya lattice pattern on top and bottom, calligraphic flowing curves on left and right sides, crescent moon and star medallions at all four corners, deep royal blue and silver on black background, empty black center, picture frame style, no text, no people. IMPORTANT: center must be completely empty black.'
    },
    {
        'filename': 'frame_route.png',
        'prompt': 'MANDATORY: Generate this image in EMERALD GREEN and GOLD colors only. The decorative border frame ornaments MUST be green colored, NOT white or grey. Arabic decorative border frame, geometric diamond tessellation on top and bottom edges, arabesque vine pattern on left and right sides, compass rose medallions at all four corners, emerald green and gold on black background, empty black center, picture frame style, no text, no people. IMPORTANT: center must be completely empty black.'
    },
    {
        'filename': 'frame_place.png',
        'prompt': 'MANDATORY: Generate this image in DEEP PURPLE and SILVER colors only. The decorative border frame ornaments MUST be purple and silver colored, NOT white or grey. Arabic decorative border frame, Qatari arch motifs on top edge, geometric star tessellation on bottom edge, arabesque floral on left and right sides, minaret silhouettes at all four corners, deep purple and silver on black background, empty black center, picture frame style, no text, no people. IMPORTANT: center must be completely empty black.'
    },
]

for img in images:
    print(f"Generating {img['filename']}...")
    try:
        response = requests.post(
            'https://api.fanar.qa/v1/images/generations',
            headers={'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'},
            json={'model': 'Fanar-Oryx-IG-2', 'prompt': img['prompt'], 'n': 1, 'size': '1024x1024'},
            timeout=90
        )
        data = response.json()
        if 'data' in data:
            item = data['data'][0]
            if item.get('b64_json'):
                out_path = os.path.join(FRONTEND_DIR, img['filename'])
                with open(out_path, 'wb') as f:
                    f.write(base64.b64decode(item['b64_json']))
                print(f"  Saved: {out_path}")
            elif item.get('url'):
                print(f"  URL: {item['url']}")
            else:
                print(f"  No image data in response: {list(item.keys())}")
        else:
            print(f"  Error: {data.get('error', data)}")
    except Exception as e:
        print(f"  Exception: {e}")

print("Done.")
