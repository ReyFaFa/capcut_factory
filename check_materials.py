import json

def go():
    try:
        with open('d:/01_Antigravity/05 capcut-motion-automation/작업지시서/draft_content - 복사본.json', 'r', encoding='utf-8') as f:
            d = json.load(f)
        
        mats = d.get('materials', {})
        res = {
            "material_keys": list(mats.keys())
        }
        
        # Check if any keyframes are in materials
        if 'keyframes' in mats:
            res['keyframes_count'] = len(mats['keyframes'])
            res['keyframes_sample'] = mats['keyframes'][:2]
            
        with open('d:/01_Antigravity/05 capcut-motion-automation/materials_check.json', 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=2)
            
    except Exception as e:
        with open('d:/01_Antigravity/05 capcut-motion-automation/materials_check.json', 'w', encoding='utf-8') as f:
            f.write(str(e))

if __name__ == '__main__':
    go()
