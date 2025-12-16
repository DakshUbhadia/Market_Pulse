/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require("fs");
const path = require("path");


const targetPath = path.join(__dirname, "..", "node_modules", "tsconfig.base.json");

const content = {
  compilerOptions: {
    target: "ES2020",
    module: "ESNext",
    moduleResolution: "Bundler",
    lib: ["ESNext", "DOM", "DOM.Iterable"],
    strict: false,
    skipLibCheck: true,
  },
};

try {
  if (!fs.existsSync(targetPath)) {
    fs.writeFileSync(targetPath, JSON.stringify(content, null, 2) + "\n", "utf8");
    console.log(`[postinstall] Wrote ${targetPath}`);
  }
} catch (err) {
  console.warn("[postinstall] Failed to write tsconfig.base.json shim:", err);
}

function patchBetterAuthPackageTsconfig(packageName) {
  const tsconfigPath = path.join(
    __dirname,
    "..",
    "node_modules",
    "@better-auth",
    packageName,
    "tsconfig.json"
  );

  if (!fs.existsSync(tsconfigPath)) return;

  try {
    const raw = fs.readFileSync(tsconfigPath, "utf8");
    const patched = raw.replace(
      '"extends": "../../tsconfig.base.json"',
      '"extends": "../../../tsconfig.json"'
    );

    if (patched !== raw) {
      fs.writeFileSync(tsconfigPath, patched, "utf8");
      console.log(`[postinstall] Patched ${tsconfigPath}`);
    }
  } catch (err) {
    console.warn(`[postinstall] Failed to patch ${tsconfigPath}:`, err);
  }
}

patchBetterAuthPackageTsconfig("core");
patchBetterAuthPackageTsconfig("telemetry");
