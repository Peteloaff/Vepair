import Link from "next/link";

export const metadata = {
  title: "Terms of Service — VepAIr",
};

export default function TermsPage() {
  return (
    <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-12">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">Terms of Service</h1>
      <p className="mb-8 text-sm text-neutral-500">Last updated August 13, 2026.</p>

      <div className="space-y-8 text-sm leading-relaxed text-neutral-300">
        <section>
          <h2 className="mb-2 text-base font-medium text-neutral-100">1. What VepAIr is</h2>
          <p>
            VepAIr is a voice conditioning and progress-tracking tool. It measures your voice
            from recordings you provide and shows you how those measurements change over time.
            <strong className="text-neutral-100"> VepAIr is not a medical device</strong> and does
            not diagnose, treat, or provide medical advice. Nothing in the app is a substitute
            for seeing a doctor, an ENT, or a qualified voice professional — if you have pain,
            sudden voice loss, breathing difficulty, or any other concerning symptom, seek
            professional care.
          </p>
        </section>

        <section>
          <h2 className="mb-2 text-base font-medium text-neutral-100">2. Your account</h2>
          <p>
            You&apos;re responsible for keeping your password secure and for anything that
            happens under your account. Create separate accounts if you use VepAIr both as a
            singer and, separately, as a coach — the two are not the same account by design.
          </p>
        </section>

        <section>
          <h2 className="mb-2 text-base font-medium text-neutral-100">
            3. Your voice recordings
          </h2>
          <p className="mb-3">
            When you record with VepAIr, we store that recording so we can analyze it and show
            you your own measurements and history. That stored copy is yours — you can delete
            your account at any time (see Section 5) to permanently remove it, and everything
            derived from it, from our systems.
          </p>
          <p className="mb-3">
            <strong className="text-neutral-100">
              We do not hold your voice recordings for coaches or any other third party.
            </strong>{" "}
            If you choose to connect with a coach and explicitly share the &quot;recordings&quot;
            category with them, they can listen to your own single stored recording through an
            authenticated link — we never make or store a second copy for them. Turning that
            sharing off, or disconnecting from the coach, cuts off their access immediately. This
            data-handling detail is separate from clinical advice: coaches on VepAIr are not
            providing medical care, and nothing they write in a note is a diagnosis.
          </p>
          <p>
            If you save or download a recording to your own device, what you do with that copy
            is your own responsibility — deleting it from VepAIr does not reach a copy you&apos;ve
            already saved elsewhere.
          </p>
        </section>

        <section>
          <h2 className="mb-2 text-base font-medium text-neutral-100">
            4. Coach connections
          </h2>
          <p>
            If you use VepAIr Coach, sharing is opt-in and per-category — nothing about your
            data is visible to a coach until you explicitly accept their invite and choose what
            to share. You can revoke that sharing at any time. Revoking stops future access
            immediately; it does not retroactively un-show anything a coach already viewed.
          </p>
        </section>

        <section>
          <h2 className="mb-2 text-base font-medium text-neutral-100">
            5. Deleting your account
          </h2>
          <p>
            You can permanently delete your account at any time from{" "}
            <Link href="/settings" className="underline hover:text-neutral-100">
              Settings
            </Link>
            . Deleting your account is permanent and cannot be undone. It removes your account,
            every recording you&apos;ve uploaded — the actual audio files, not just a database
            reference to them — and everything derived from them: check-ins, measurements, vocal
            range history, exercise history, coach connections, and notes. This is wiped from
            our systems, not just hidden from view.
          </p>
        </section>

        <section>
          <h2 className="mb-2 text-base font-medium text-neutral-100">
            6. Disclaimers and limits
          </h2>
          <p>
            VepAIr is provided &quot;as is.&quot; Voice measurements can be affected by your
            microphone, environment, and many other factors, and are not a substitute for
            professional evaluation. To the extent permitted by law, VepAIr is not liable for
            decisions you make based on the app&apos;s measurements or feedback.
          </p>
        </section>

        <section>
          <h2 className="mb-2 text-base font-medium text-neutral-100">7. Changes</h2>
          <p>
            We may update these terms as VepAIr changes. If we make a material change, we&apos;ll
            update the date at the top of this page.
          </p>
        </section>

        <section>
          <h2 className="mb-2 text-base font-medium text-neutral-100">8. Contact</h2>
          <p>
            Questions about these terms or your data can be sent to{" "}
            <a href="mailto:support@vepair.com" className="underline hover:text-neutral-100">
              support@vepair.com
            </a>
            .
          </p>
        </section>
      </div>
    </main>
  );
}
