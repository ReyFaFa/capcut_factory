import json

def extract_segments():
    f1 = 'd:/01_Antigravity/05 capcut-motion-automation/작업지시서/draft_content.json'
    f2 = 'd:/01_Antigravity/05 capcut-motion-automation/작업지시서/draft_content - 복사본.json'
    
    with open(f1, 'r', encoding='utf-8') as f:
        d1 = json.load(f)
    with open(f2, 'r', encoding='utf-8') as f:
        d2 = json.load(f)
        
    v1 = [t for t in d1.get('tracks', []) if t.get('type') == 'video']
    v2 = [t for t in d2.get('tracks', []) if t.get('type') == 'video']
    
    s1 = v1[0]['segments'][0] if v1 and v1[0].get('segments') else {}
    s2 = v2[0]['segments'][0] if v2 and v2[0].get('segments') else {}
    
    with open('d:/01_Antigravity/05 capcut-motion-automation/segment_current.json', 'w', encoding='utf-8') as f:
        json.dump(s1, f, indent=2, ensure_ascii=False)
        
    with open('d:/01_Antigravity/05 capcut-motion-automation/segment_backup.json', 'w', encoding='utf-8') as f:
        json.dump(s2, f, indent=2, ensure_ascii=False)
        
if __name__ == '__main__':
    extract_segments()
