"use client";

import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { USER_GUIDE_HTML } from "./content";

export default function UserGuidePage() {
  return (
    <RequireAuth>
      <main className="flex flex-1 flex-col px-6 py-6">
        <Link
          href="/help"
          className="mb-4 inline-block w-fit text-xs text-neutral-500 hover:text-neutral-300"
        >
          &larr; Back to Help
        </Link>
        {/* Rendered in an isolated iframe (srcDoc, not a remote URL) rather than inline in this
            page's own DOM -- this document brings its own full CSS reset (:root tokens, `* {
            box-sizing }`, `a { color: inherit }`, ...) that would otherwise collide with the
            TopNav/footer this same page also renders. The iframe gets its own document, so
            neither side's styling can leak into the other, and it never leaves vepair.com or
            opens an external site the way a link to a hosted document would. */}
        <iframe
          srcDoc={USER_GUIDE_HTML}
          title="VepAIr User Guide"
          className="min-h-[80vh] w-full flex-1 rounded-2xl border border-neutral-800"
        />
      </main>
    </RequireAuth>
  );
}
