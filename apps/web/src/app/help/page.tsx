import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";

function FeatureCard({
  title,
  where,
  children,
}: {
  title: string;
  where?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-medium text-neutral-200">{title}</h3>
        {where && (
          <span className="rounded-full bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400">
            {where}
          </span>
        )}
      </div>
      <div className="space-y-2 text-sm text-neutral-400">{children}</div>
    </div>
  );
}

function Steps({ items }: { items: React.ReactNode[] }) {
  return (
    <ol className="ml-4 list-decimal space-y-1.5 text-sm text-neutral-400 marker:text-neutral-600">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ol>
  );
}

function Callout({
  tone,
  children,
}: {
  tone: "info" | "note" | "warn";
  children: React.ReactNode;
}) {
  const styles = {
    info: "border border-neutral-700 bg-neutral-900 text-neutral-400",
    note: "bg-emerald-950/30 text-emerald-300",
    warn: "bg-red-950/40 text-red-300",
  }[tone];
  return <p className={`rounded-lg px-3 py-2 text-xs ${styles}`}>{children}</p>;
}

export default function HelpPage() {
  return (
    <RequireAuth>
      <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-12">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">Help</h1>
        <p className="mb-10 text-sm text-neutral-400">
          What&apos;s new in VepAIr, and how to use it. This release is built around one idea:
          you get to say what you&apos;re training toward. VepAIr will still suggest sensible
          targets from your own history, but every suggestion is now something you can see,
          question, and override.
        </p>

        <section className="mb-10">
          <h2 className="mb-4 text-xs font-medium uppercase tracking-wide text-neutral-500">
            How it works
          </h2>
          <FeatureCard title="How VepAIr adapts to you">
            <p>
              Nothing in VepAIr is measured against anyone else&apos;s voice. Every exercise,
              every piece of live feedback, and every target note comes from one loop: compare
              today against your own history, then adjust. It repeats every time you practice:
            </p>
            <Steps
              items={[
                <>
                  <strong className="text-neutral-200">Record &amp; measure</strong> — every
                  recording gets its pitch and quality measured automatically.
                </>,
                <>
                  <strong className="text-neutral-200">Your personal baseline</strong> — those
                  measurements build a picture of what&apos;s normal for you specifically, never a
                  population average.
                </>,
                <>
                  <strong className="text-neutral-200">Recovery score &amp; safety check</strong> —
                  today is checked against your baseline; an off day gets flagged, and several
                  rough days in a row can trigger a rest-day recommendation.
                </>,
                <>
                  <strong className="text-neutral-200">Adaptive daily routine</strong> —
                  today&apos;s exercises are picked and sequenced from where your baseline says
                  you are right now.
                </>,
                <>
                  <strong className="text-neutral-200">Live coaching &amp; Goal Tones</strong> —
                  while you sing, real-time feedback compares your voice against a target: your
                  Goal Tone, a coach&apos;s target, or the exercise&apos;s own.
                </>,
                <>
                  <strong className="text-neutral-200">Track growth over time</strong> — vocal
                  range, exercise trends, and your plan all update from what just happened, then
                  feed straight back into step one next time you practice.
                </>,
              ]}
            />
            <Callout tone="info">
              The loop never stops — every new recording refines the baseline everything else is
              measured against.
            </Callout>
          </FeatureCard>
        </section>

        <section className="mb-10">
          <h2 className="mb-4 text-xs font-medium uppercase tracking-wide text-emerald-400">
            For everyone
          </h2>
          <div className="space-y-3">
            <FeatureCard title="Goal Tones — set your own low, average, and high target" where="Tone Match">
              <p>
                VepAIr already suggests a stretch target from your measured vocal range. Goal
                Tones makes that suggestion visible and editable: three target notes — Low,
                Average, and High — that drive your daily exercises and the summary card on your
                home page.
              </p>
              <Steps
                items={[
                  <>
                    Open <strong className="text-neutral-200">Tone Match</strong>. Your current
                    targets are shown as three note pickers, labeled either{" "}
                    <span className="rounded-full bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400">
                      AI-suggested
                    </span>{" "}
                    or{" "}
                    <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-300">
                      Your target
                    </span>{" "}
                    once you&apos;ve set your own.
                  </>,
                  <>
                    Pick new notes for any of Low / Average / High, then select{" "}
                    <strong className="text-neutral-200">Save my targets</strong>.
                  </>,
                  <>
                    Changed your mind?{" "}
                    <strong className="text-neutral-200">Reset to AI suggestion</strong> clears
                    your override and goes back to a live recommendation.
                  </>,
                ]}
              />
              <Callout tone="info">
                No vocal range test yet? Do one first, or just set your own targets manually any
                time.
              </Callout>
            </FeatureCard>

            <FeatureCard title="Find your average pitch" where="Tone Match">
              <p>
                An open-ended recorder for the times a quick sustained note isn&apos;t what you
                want to measure — speaking naturally, warming up, or singing through a phrase.
              </p>
              <Steps
                items={[
                  <>
                    Select <strong className="text-neutral-200">Start recording</strong> and
                    speak or sing for as long as you like.
                  </>,
                  <>
                    Select <strong className="text-neutral-200">Stop</strong> when
                    you&apos;re done. VepAIr shows the average pitch across the whole recording,
                    as both a note name and Hz.
                  </>,
                  <>
                    Like the result?{" "}
                    <strong className="text-neutral-200">Use as my Avg goal tone</strong> saves it
                    straight into your Average target from Goal Tones.
                  </>,
                ]}
              />
              <Callout tone="note">
                This recording also counts toward your personal baseline, same as any other
                sample.
              </Callout>
            </FeatureCard>

            <FeatureCard title="Rest day recommendations" where="Home & Voice exercises">
              <p>
                On days your recent numbers suggest your voice needs a break, you&apos;ll see a
                message like this at the top of your home page and exercise screen:
              </p>
              <Callout tone="warn">
                &ldquo;Today looks like a good day to rest your voice completely. If this
                continues, consider checking in with a qualified voice professional.&rdquo;
              </Callout>
              <p>
                This shows up after several consecutive lower-recovery days, or significant
                reported discomfort. It&apos;s a recommendation, not a lock — your exercises are
                still there, kept to the gentlest, safest options. Nothing about VepAIr will ever
                refuse to let you train.
              </p>
            </FeatureCard>

            <FeatureCard title="Exercise info buttons" where="Everywhere exercises are listed">
              <p>
                A small circled <span className="font-mono">i</span> next to any exercise name
                reveals what it&apos;s for, how to do it, and any cautions.
              </p>
              <Steps
                items={[
                  "On a computer, hover over it to see the details.",
                  "On a phone or tablet, tap it to open the same panel, and tap again to close.",
                ]}
              />
            </FeatureCard>

            <FeatureCard title="Account & privacy" where="Settings">
              <p>
                Not new this release, but worth knowing about: from{" "}
                <Link href="/settings" className="text-emerald-400 hover:text-emerald-300">
                  Settings
                </Link>{" "}
                you can review the{" "}
                <Link href="/terms" className="text-emerald-400 hover:text-emerald-300">
                  Terms of Service
                </Link>{" "}
                and permanently delete your account — including every recording&apos;s actual
                audio file, not just the database record. Confirm your password and type{" "}
                <span className="font-mono text-red-300">DELETE</span> to enable the final
                button. This cannot be undone.
              </p>
            </FeatureCard>
          </div>
        </section>

        <section className="mb-10">
          <h2 className="mb-4 text-xs font-medium uppercase tracking-wide text-violet-400">
            For coaches
          </h2>
          <div className="space-y-3">
            <FeatureCard title="Your home page, not a redirect">
              <p>
                Signing in as a coach used to jump you straight to the Coach Portal. Now you land
                on the same home page every singer sees, with the singer-only sections replaced
                by a compact panel and a link into your Coach Portal.
              </p>
            </FeatureCard>

            <FeatureCard title="Build your own exercises" where="Assign training">
              <p>
                If the exercise library is missing something a singer needs, add it yourself — no
                waiting on VepAIr to build it in.
              </p>
              <Steps
                items={[
                  <>
                    From a singer&apos;s <strong className="text-neutral-200">Assign training</strong>{" "}
                    page, select <strong className="text-neutral-200">+ Add custom exercise</strong>.
                  </>,
                  <>
                    Fill in a <strong className="text-neutral-200">Title</strong> and{" "}
                    <strong className="text-neutral-200">Description</strong>, then choose a
                    category, difficulty, and duration.
                  </>,
                  <>
                    Select <strong className="text-neutral-200">Save exercise</strong>. It&apos;s
                    added to the library immediately and pre-selected, ready to assign.
                  </>,
                ]}
              />
              <Callout tone="info">
                Categories are a fixed list rather than free text — that&apos;s what keeps every
                custom exercise inside the same safety limits as the exercises VepAIr ships with.
              </Callout>
            </FeatureCard>

            <FeatureCard title="A target tone for one exercise" where="Assign training">
              <p>
                When assigning exercises, attach an optional target note to any exercise
                you&apos;ve selected — useful for a specific pitch you want a singer focused on
                during that one exercise. It&apos;s informational only and never changes what&apos;s
                safe for them that day.
              </p>
            </FeatureCard>
          </div>
        </section>

        <section>
          <h2 className="mb-4 text-xs font-medium uppercase tracking-wide text-neutral-500">
            Quick answers
          </h2>
          <div className="space-y-3">
            <FeatureCard title="If I set my own Goal Tones, does the AI suggestion disappear?">
              <p>It&apos;s replaced, not deleted — Reset to AI suggestion brings it back any time.</p>
            </FeatureCard>
            <FeatureCard title="Can I still exercise on a recommended rest day?">
              <p>Yes. It&apos;s guidance, never a block.</p>
            </FeatureCard>
            <FeatureCard title="Does a coach's custom exercise only show up for their own singers?">
              <p>No — once saved, it&apos;s a normal library exercise available to anyone&apos;s daily routine.</p>
            </FeatureCard>
          </div>
        </section>

        <p className="mt-10 text-xs text-neutral-500">
          VepAIr is a training and tracking tool, not a medical device. Rest day recommendations
          and every other suggestion here are guidance based on your own data, never a diagnosis
          or clinical instruction. If something feels wrong with your voice, check in with a
          qualified voice professional.
        </p>
      </main>
    </RequireAuth>
  );
}
