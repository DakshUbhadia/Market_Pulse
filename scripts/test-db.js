/* eslint-disable @typescript-eslint/no-require-imports */
// Simple DB test script (CommonJS)
// Usage: node scripts/test-db.js

const mongoose = require('mongoose');
const fs = require('fs');
const path = require('path');

// __dirname is available in CommonJS
const envPath = path.join(__dirname, '..', '.env');

// Load .env if dotenv is installed
try {
  require('dotenv').config({ path: envPath });
} catch {
  // proceed; we'll parse manually if needed
}

function loadEnvIfMissing() {
  if (process.env.MONGODB_URI) return;
  try {
    if (!fs.existsSync(envPath)) return;
    const raw = fs.readFileSync(envPath, 'utf8');
    raw.split(/\r?\n/).forEach((line) => {
      line = line.trim();
      if (!line || line.startsWith('#')) return;
      const idx = line.indexOf('=');
      if (idx === -1) return;
      let key = line.slice(0, idx).trim();
      let val = line.slice(idx + 1).trim();
      if ((val.startsWith("'") && val.endsWith("'")) || (val.startsWith('"') && val.endsWith('"'))) {
        val = val.slice(1, -1);
      }
      process.env[key] = val;
    });
  } catch {
    // ignore
  }
}

loadEnvIfMissing();

const MONGODB_URI = process.env.MONGODB_URI;

if (!MONGODB_URI) {
  console.error('MONGODB_URI is not set. Check your .env file.');
  process.exit(1);
}

function ensureSafeMongoUri(uri) {
  try {
    const m = uri.match(/(^mongodb(?:\+srv)?:\/\/)([^:]+):([^@]+)@(.*)$/);
    if (!m) return uri;
    const scheme = m[1];
    const user = m[2];
    const pass = m[3];
    const rest = m[4];
    const safePass = encodeURIComponent(pass);
    if (safePass === pass) return uri;
    return `${scheme}${user}:${safePass}@${rest}`;
  } catch {
    return uri;
  }
}

const SAFE_MONGODB_URI = ensureSafeMongoUri(MONGODB_URI);

function shortHost(uri) {
  try {
    const m = uri.match(/@(.+)$/);
    if (!m) return '(unknown host)';
    return m[1].split('/')[0];
  } catch {
    return '(unknown host)';
  }
}

(async function run() {
  try {
    console.log(`Connecting to MongoDB host: ${shortHost(SAFE_MONGODB_URI)}...`);
    await mongoose.connect(SAFE_MONGODB_URI);
    console.log('Connected to MongoDB successfully.');
    console.log('Mongoose connection readyState =', mongoose.connection.readyState);
    await mongoose.disconnect();
    console.log('Disconnected. Test complete.');
    process.exit(0);
  } catch (err) {
    console.error('Failed to connect to MongoDB.');
    if (err && err.message) console.error(err.message);
    else console.error(err);
    process.exit(2);
  }
})();
