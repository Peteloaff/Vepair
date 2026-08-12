"use client"; // Error boundaries must be Client Components

export default function GlobalError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col items-center justify-center gap-4 bg-neutral-950 text-neutral-100">
        <h2 className="text-lg font-semibold">Something went wrong.</h2>
        <p className="max-w-sm text-center text-sm text-neutral-400">{error.message}</p>
        <button
          type="button"
          onClick={() => retry()}
          className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800"
        >
          Try again
        </button>
      </body>
    </html>
  );
}
