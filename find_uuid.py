import json

def find_paths(obj, target, current_path=""):
    paths = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            paths.extend(find_paths(v, target, f"{current_path}.{k}" if current_path else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            paths.extend(find_paths(v, target, f"{current_path}[{i}]"))
    elif isinstance(obj, str):
        if target in obj:
            paths.append(current_path)
    return paths

if __name__ == '__main__':
    with open('d:/01_Antigravity/05 capcut-motion-automation/작업지시서/draft_content - 복사본.json', 'r', encoding='utf-8') as f:
        d = json.load(f)
    paths = find_paths(d, "538DEEC7-AE2F-4BE4-B18E-3DD4FC7C60EE")
    print("Found at:")
    for p in paths:
        print(p)
