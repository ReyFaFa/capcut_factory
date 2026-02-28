const fs = require('fs');
const d1 = JSON.parse(fs.readFileSync('d:/01_Antigravity/05 capcut-motion-automation/작업지시서/draft_content.json', 'utf8'));
const d2 = JSON.parse(fs.readFileSync('d:/01_Antigravity/05 capcut-motion-automation/작업지시서/draft_content - 복사본.json', 'utf8'));

const v1 = d1.tracks.find(t => t.type === 'video').segments[0];
const v2 = d2.tracks.find(t => t.type === 'video').segments[0];

const out = {
    current_clip: v1.clip,
    backup_clip: v2.clip,
    current_kf_len: v1.common_keyframes?.length,
    backup_kf_len: v2.common_keyframes?.length,
    backup_kf_sample: v2.common_keyframes
};

fs.writeFileSync('d:/01_Antigravity/05 capcut-motion-automation/output.json', JSON.stringify(out, null, 2));
console.log('done');
