export function CodeBlock({ code, tone = "default" }: { code: string; tone?: "default" | "error" }) {
  return <pre className={`code-block ${tone === "error" ? "code-block-error" : ""}`}>{code}</pre>;
}
