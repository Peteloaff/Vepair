export interface HealthResponse {
  status: string;
  database: string;
  app_env: string;
}

export interface HealthCheckResult {
  ok: boolean;
  data: HealthResponse | null;
  error: string | null;
}

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

export async function getHealth(): Promise<HealthCheckResult> {
  try {
    const res = await fetch(`${API_URL}/api/v1/health`, { cache: "no-store" });
    if (!res.ok) {
      return { ok: false, data: null, error: `Backend responded with ${res.status}` };
    }
    const data = (await res.json()) as HealthResponse;
    return { ok: true, data, error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return { ok: false, data: null, error: message };
  }
}
