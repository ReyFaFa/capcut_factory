import json
import sys
import traceback

def extract_kf():
    try:
        f1 = 'd:/01_Antigravity/05 capcut-motion-automation/작업지시서/draft_content.json'
        f2 = 'd:/01_Antigravity/05 capcut-motion-automation/작업지시서/draft_content - 복사본.json'
        
        with open(f2, 'r', encoding='utf-8') as f:
            d2 = json.load(f)
            
        with open(f1, 'r', encoding='utf-8') as f:
            d1 = json.load(f)
            
        v2 = [t for t in d2.get('tracks', []) if t.get('type') == 'video']
        if not v2 or not v2[0].get('segments'):
            print("No video segments in backup")
            return
            
        s2 = v2[0]['segments'][0]
        
        v1 = [t for t in d1.get('tracks', []) if t.get('type') == 'video']
        s1 = v1[0]['segments'][0] if v1 and v1[0].get('segments') else {}
        
        out = {
            "current_clip": s1.get('clip', {}),
            "backup_clip": s2.get('clip', {}),
            "current_kf_len": len(s1.get('common_keyframes', [])),
            "backup_kf_len": len(s2.get('common_keyframes', [])),
            "backup_kf_sample": s2.get('common_keyframes', [])
        }
        
        with open('d:/01_Antigravity/05 capcut-motion-automation/kf_compare.json', 'w', encoding='utf-8') as out_f:
            json.dump(out, out_f, indent=2, ensure_ascii=False)
            
        print("Successfully extracted to kf_compare.json")
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    extract_kf()
