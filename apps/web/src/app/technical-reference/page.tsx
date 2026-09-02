"use client";

import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { TECHNICAL_REFERENCE_HTML } from "./content";

export default function TechnicalReferencePage() {
  return (
    <RequireAuth>
      <main className="flex flex-1 flex-col px-6 py-6">
        <Link
          href="/help"
          className="mb-4 inline-block w-fit text-xs text-neutral-500 hover:text-neutral-300"
        >
          &larr; Back to Help
        </Link>
        {/* Isolated iframe for the same reason as /user-guide -- this document brings its own
            full CSS reset that would otherwise collide with the TopNav/footer this page also
            renders, and it keeps everything on vepair.com rather than an external link. */}
        <iframe
          srcDoc={TECHNICAL_REFERENCE_HTML}
          title="VepAIr Technical Reference"
          className="min-h-[80vh] w-full flex-1 rounded-2xl border border-neutral-800"
        />
      </main>
    </RequireAuth>
  );
}
