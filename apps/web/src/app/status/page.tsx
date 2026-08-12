import { getHealth } from "@/lib/api";

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${
        ok ? "bg-emerald-400" : "bg-red-500"
      }`}
      aria-hidden
    />
  );
}

export default async function StatusPage() {
  const health = await getHealth();
  const dbOk = health.data?.database === "connected";

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-10 px-6 py-16">
      <div className="text-center">
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">VepAIr</h1>
        <p className="mt-3 text-sm text-neutral-400">System diagnostics</p>
      </div>

      <section className="w-full max-w-md rounded-2xl border border-neutral-800 bg-neutral-900/60 p-6">
        <h2 className="mb-4 text-xs font-medium tracking-wide text-neutral-400 uppercase">
          System status
        </h2>

        <dl className="space-y-3 text-sm">
          <div className="flex items-center justify-between">
            <dt className="text-neutral-400">API</dt>
            <dd className="flex items-center gap-2 font-medium">
              <StatusDot ok={health.ok} />
              {health.ok ? "Reachable" : "Unreachable"}
            </dd>
          </div>

          <div className="flex items-center justify-between">
            <dt className="text-neutral-400">Database</dt>
            <dd className="flex items-center gap-2 font-medium">
              <StatusDot ok={dbOk} />
              {health.data?.database ?? "Unknown"}
            </dd>
          </div>

          <div className="flex items-center justify-between">
            <dt className="text-neutral-400">Environment</dt>
            <dd className="font-medium">{health.data?.app_env ?? "n/a"}</dd>
          </div>
        </dl>

        {!health.ok && (
          <p className="mt-4 rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">
            {health.error}
          </p>
        )}
      </section>

      <p className="max-w-md text-center text-xs text-neutral-500">
        This page proves the frontend can reach the backend and the backend can reach the
        database.
      </p>
    </main>
  );
}
