// Cross-platform copy is permitted only for architecture-independent production dependencies.
import fs from 'node:fs';
import path from 'node:path';
let count = 0;
function walk(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const filename = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      walk(filename);
    } else if (entry.isFile()) {
      if (entry.name.endsWith('.node')) throw new Error('Native Node addon cannot be copied across architectures');
      const fd = fs.openSync(filename, 'r');
      const head = Buffer.alloc(4);
      fs.readSync(fd, head, 0, 4, 0);
      fs.closeSync(fd);
      const signature = head.toString('hex');
      if (['7f454c46', 'cffaedfe', 'cefaedfe', 'feedfacf', 'feedface', 'cafebabe'].includes(signature)) {
        throw new Error('Native executable found in production dependencies; AMD64-native build required');
      }
      count++;
    }
  }
}
walk('node_modules');
console.log(`Verified ${count} production dependency files without native addons/executables.`);
