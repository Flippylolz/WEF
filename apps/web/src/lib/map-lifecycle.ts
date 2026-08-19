/** Test-only instrumentation for MapLibre construction count regressions. */

let constructionCount = 0;

export function resetMapConstructionCount(): void {
  constructionCount = 0;
}

export function getMapConstructionCount(): number {
  return constructionCount;
}

export function recordMapConstruction(): void {
  if (process.env.NODE_ENV === "test") {
    constructionCount += 1;
  }
}
