const fs = require('fs');
const d = JSON.parse(fs.readFileSync('d:/01_Antigravity/05 capcut-motion-automation/작업지시서/draft_content - 복사본.json', 'utf8'));
const target = '538DEEC7-AE2F-4BE4-B18E-3DD4FC7C60EE';

function findPaths(obj, target, currentPath = '') {
    let paths = [];
    if (typeof obj === 'string') {
        if (obj.includes(target)) paths.push(currentPath);
    } else if (Array.isArray(obj)) {
        for (let i = 0; i < obj.length; i++) {
            paths.push(...findPaths(obj[i], target, currentPath ? `${currentPath}[${i}]` : `[${i}]`));
        }
    } else if (obj !== null && typeof obj === 'object') {
        for (const [k, v] of Object.entries(obj)) {
            paths.push(...findPaths(v, target, currentPath ? `${currentPath}.${k}` : k));
        }
    }
    return paths;
}

const paths = findPaths(d, target);
fs.writeFileSync('d:/01_Antigravity/05 capcut-motion-automation/uuid_paths.txt', paths.join('\n'));
console.log('done');
