// Pre-mapped skill adjacency graph. Each key maps to skills considered
// "structurally adjacent" — a candidate with the neighbors is one short hop
// away from the missing skill.

export const SKILL_ADJACENCY: Record<string, string[]> = {
  kubernetes: ["docker", "helm", "terraform", "aws ecs", "containerd"],
  docker: ["kubernetes", "podman", "containerd", "ci/cd"],
  terraform: ["aws", "gcp", "azure", "pulumi", "ansible"],
  react: ["next.js", "remix", "vue", "svelte", "typescript"],
  "next.js": ["react", "remix", "tanstack start", "vercel"],
  typescript: ["javascript", "react", "node.js"],
  python: ["fastapi", "django", "flask", "pandas", "numpy"],
  pytorch: ["tensorflow", "jax", "numpy", "python"],
  tensorflow: ["pytorch", "keras", "jax", "python"],
  pandas: ["numpy", "python", "polars", "spark"],
  "node.js": ["typescript", "express", "fastify", "nest.js"],
  postgres: ["mysql", "sqlite", "supabase", "sql"],
  aws: ["gcp", "azure", "terraform", "cloudformation"],
  graphql: ["rest", "apollo", "trpc"],
  rust: ["go", "c++", "wasm"],
  go: ["rust", "java", "c++"],
  langchain: ["llamaindex", "openai api", "python", "rag"],
  rag: ["langchain", "vector db", "embeddings", "openai api"],
  "vector db": ["pinecone", "weaviate", "qdrant", "pgvector"],
  spark: ["hadoop", "pandas", "scala", "databricks"],
  airflow: ["dagster", "prefect", "luigi"],
  fastapi: ["flask", "django", "python", "starlette"],
};

export function getAdjacentSkills(skill: string): string[] {
  return SKILL_ADJACENCY[skill.toLowerCase()] ?? [];
}

/**
 * For a list of required skills the candidate is MISSING, what fraction of
 * those missing skills do they have a documented adjacent skill for?
 * Returns 0..1.
 */
export function adjacencyCoverage(
  missingRequired: string[],
  candidateSkills: string[],
): number {
  if (missingRequired.length === 0) return 1;
  const lowerCand = new Set(candidateSkills.map((s) => s.toLowerCase()));
  let covered = 0;
  for (const m of missingRequired) {
    const neighbors = getAdjacentSkills(m);
    if (neighbors.some((n) => lowerCand.has(n))) covered++;
  }
  return covered / missingRequired.length;
}
