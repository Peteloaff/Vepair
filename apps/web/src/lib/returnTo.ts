// Where to send someone after they log in. RequireAuth passes the page they were trying to reach
// as ?next=; only plain in-app paths are honored, so the parameter can't be used to bounce a
// user to another site.
export function safeNextPath(): string {
  if (typeof window === "undefined") return "/";
  const next = new URLSearchParams(window.location.search).get("next");
  if (next && next.startsWith("/") && !next.startsWith("//") && !next.startsWith("/\\")) {
    return next;
  }
  return "/";
}
