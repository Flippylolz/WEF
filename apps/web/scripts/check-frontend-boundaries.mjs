import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";
import ts from "typescript";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
function filesUnder(path) {
  return readdirSync(path, { withFileTypes: true }).flatMap((entry) => {
    const file = join(path, entry.name);
    return entry.isDirectory() ? filesUnder(file) : [file];
  });
}
const sources = filesUnder(join(root, "src")).filter(
  (file) => /\.tsx?$/.test(file) && !/\.test[.-]|\/test\//.test(file),
);
const graph = new Map();
for (const file of sources) {
  const source = ts.createSourceFile(
    file,
    readFileSync(file, "utf8"),
    ts.ScriptTarget.Latest,
    true,
  );
  const edges = [];
  function add(specifier) {
    const base = specifier.startsWith("@/")
      ? join(root, "src", specifier.slice(2))
      : specifier.startsWith(".")
        ? resolve(dirname(file), specifier)
        : null;
    if (base === null) return;
    const target = [
      base,
      `${base}.ts`,
      `${base}.tsx`,
      join(base, "index.ts"),
      join(base, "index.tsx"),
    ].find((candidate) => sources.includes(candidate));
    if (target) edges.push(target);
  }
  function visit(node) {
    if (
      (ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) &&
      node.moduleSpecifier &&
      ts.isStringLiteral(node.moduleSpecifier)
    )
      add(node.moduleSpecifier.text);
    if (
      ts.isCallExpression(node) &&
      node.expression.kind === ts.SyntaxKind.ImportKeyword &&
      node.arguments[0] &&
      ts.isStringLiteral(node.arguments[0])
    )
      add(node.arguments[0].text);
    ts.forEachChild(node, visit);
  }
  visit(source);
  graph.set(file, edges);
}
const visited = new Set();
function check(file, stack = []) {
  if (stack.includes(file))
    throw new Error(
      `Frontend import cycle: ${[...stack, file].map((item) => item.slice(root.length + 1)).join(" -> ")}`,
    );
  if (visited.has(file)) return;
  for (const dependency of graph.get(file) ?? [])
    check(dependency, [...stack, file]);
  visited.add(file);
}
for (const file of sources) check(file);
console.log(
  `Frontend boundaries: ${sources.length} source modules, no import cycles.`,
);
if (process.argv.includes("--bundle")) {
  const chunksRoot = join(root, ".next/static/chunks");
  if (!existsSync(chunksRoot))
    throw new Error("Production build chunks are missing");
  const chunks = filesUnder(chunksRoot).filter((file) => file.endsWith(".js"));
  if (chunks.length === 0)
    throw new Error("Production JavaScript chunks are missing");
  const bytes = chunks.reduce(
    (sum, file) => sum + gzipSync(readFileSync(file), { level: 9 }).length,
    0,
  );
  const budget = JSON.parse(
    readFileSync(join(root, "frontend-budgets.json"), "utf8"),
  );
  if (!Number.isSafeInteger(budget.maxGzipBytes) || budget.maxGzipBytes <= 0)
    throw new Error("Invalid frontend bundle budget");
  if (bytes > budget.maxGzipBytes)
    throw new Error(
      `Production JavaScript gzip bytes ${bytes} exceed ${budget.maxGzipBytes}`,
    );
  console.log(
    `Production JavaScript: ${bytes} gzip bytes across ${chunks.length} chunks (budget ${budget.maxGzipBytes}).`,
  );
}
