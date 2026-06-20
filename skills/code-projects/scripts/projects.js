const fs = require('fs');
const path = require('path');

/**
 * Look up project paths under D:\code by name or partial match.
 *
 * Usage:
 *   node projects.js <name>          # exact or partial match
 *   node projects.js --list          # list all projects
 *   node projects.js --json <name>   # output JSON for matching projects
 *
 * Examples:
 *   node projects.js euv             # finds D:\code\euv
 *   node projects.js hyperlane       # finds all hyperlane-* projects
 */

const CODE_DIR = 'D:\\code';

const args = process.argv.slice(2);

if (args.length === 0 || args[0] === '--help') {
  console.log('Usage:');
  console.log('  node projects.js --list              # list all projects');
  console.log('  node projects.js <name>              # find project(s) by name');
  console.log('  node projects.js --json <name>       # output JSON');
  console.log('  node projects.js --path <name>       # output path only');
  process.exit(args.length === 0 ? 1 : 0);
}

// Get all directories under D:\code
const allProjects = fs.readdirSync(CODE_DIR)
  .filter(name => fs.statSync(path.join(CODE_DIR, name)).isDirectory())
  .sort();

if (args[0] === '--list') {
  allProjects.forEach(p => console.log(p));
  process.exit(0);
}

const query = args[1] && (args[0] === '--json' || args[0] === '--path') ? args[1] : args[0];
const mode = args[0] === '--json' ? 'json' : args[0] === '--path' ? 'path' : 'text';

// Match: exact first, then prefix, then includes
const exact = allProjects.find(p => p.toLowerCase() === query.toLowerCase());
const prefix = allProjects.find(p => p.toLowerCase().startsWith(query.toLowerCase()));
const includes = allProjects.filter(p => p.toLowerCase().includes(query.toLowerCase()));

let results = [];
if (exact) results = [exact];
else if (prefix) results = [prefix];
else results = includes;

if (results.length === 0) {
  console.error(`No project matching "${query}" found under ${CODE_DIR}`);
  process.exit(1);
}

if (mode === 'json') {
  const output = results.map(name => ({
    name,
    path: path.join(CODE_DIR, name),
    hasGit: fs.existsSync(path.join(CODE_DIR, name, '.git')),
    hasCargo: fs.existsSync(path.join(CODE_DIR, name, 'Cargo.toml')),
    hasPackageJson: fs.existsSync(path.join(CODE_DIR, name, 'package.json')),
  }));
  console.log(JSON.stringify(output, null, 2));
} else if (mode === 'path') {
  results.forEach(p => console.log(path.join(CODE_DIR, p)));
} else {
  results.forEach(p => console.log(`${p}  →  ${path.join(CODE_DIR, p)}`));
}
