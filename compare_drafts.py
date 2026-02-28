import json
import sys

def compare_json_files(file1, file2):
    try:
        with open(file1, 'r', encoding='utf-8') as f1:
            d1 = json.load(f1)
        with open(file2, 'r', encoding='utf-8') as f2:
            d2 = json.load(f2)
            
        print(f"File 1 (Current): {file1}")
        print(f"File 2 (Backup/Working): {file2}")
        
        v1 = [t for t in d1.get('tracks', []) if t.get('type') == 'video']
        v2 = [t for t in d2.get('tracks', []) if t.get('type') == 'video']
        
        print("\n--- Track Count ---")
        print(f"Current Video Tracks: {len(v1)}")
        print(f"Working Video Tracks: {len(v2)}")
        
        if not v1 or not v2:
            print("Missing video tracks in one of the files.")
            return

        s1 = v1[0].get('segments', [])
        s2 = v2[0].get('segments', [])
        
        print("\n--- Segment Count ---")
        print(f"Current First Track Segments: {len(s1)}")
        print(f"Working First Track Segments: {len(s2)}")
        
        if not s1 or not s2:
            print("Missing segments in one of the files.")
            return

        print("\n--- First Segment Clip Info ---")
        print("Current Clip keys:", list(s1[0].get('clip', {}).keys()))
        print("Working Clip keys:", list(s2[0].get('clip', {}).keys()))
        print("Current Clip transform:", s1[0].get('clip', {}).get('transform'))
        print("Working Clip transform:", s2[0].get('clip', {}).get('transform'))
        print("Current Clip scale:", s1[0].get('clip', {}).get('scale'))
        print("Working Clip scale:", s2[0].get('clip', {}).get('scale'))
        
        print("\n--- First Segment Keyframes Info ---")
        kf1 = s1[0].get('common_keyframes', [])
        kf2 = s2[0].get('common_keyframes', [])
        print(f"Current common_keyframes length: {len(kf1)}")
        print(f"Working common_keyframes length: {len(kf2)}")
        
        if kf1:
            print(f"Current First KF Property: {kf1[0].get('property_type')}")
        if kf2:
            print(f"Working First KF Property: {kf2[0].get('property_type')}")

        print("\n--- Working common_keyframes dump ---")
        if kf2:
            for k in kf2:
                 print(json.dumps(k, indent=2))
        else:
            print("None")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    f1 = 'd:/01_Antigravity/05 capcut-motion-automation/작업지시서/draft_content.json'
    f2 = 'd:/01_Antigravity/05 capcut-motion-automation/작업지시서/draft_content - 복사본.json'
    compare_json_files(f1, f2)
