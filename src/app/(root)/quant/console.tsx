import Link from "next/link";
import { notFound } from "next/navigation";
import { canReadQuantStatus, readQuantStatus } from "@/lib/quant/status-server";
import type { QuantStatus } from "@/lib/quant/status-contract";
import { Coverage, Evidence, type Search } from "./evidence-views";
import { Card, Fields, dateLabel, details, display, measured, panel, state, type Snapshot } from "./presentation";

export const sections = [
  ["", "Overview"], ["data", "Data readiness"], ["evidence", "Evidence"], ["research", "Research"],
  ["models", "Models"], ["risk", "Risk"], ["forward", "Forward"], ["operations", "Operations"],
  ["rankings", "Rankings"], ["portfolio", "Portfolio"],
] as const;
function Provenance({ status }: { status: QuantStatus }) {
  const entries = Object.entries(details(status)?.artifacts ?? {});
  return <details className={panel}>
    <summary className="cursor-pointer font-medium text-slate-200">Snapshot provenance</summary>
    <div className="mt-3 text-sm"><Fields items={[
      ["Snapshot ID", status.runId], ["Source commit", status.gitCommit], ["Certified commit", details(status)?.certifiedSha],
      ["Input manifest", status.inputManifestHash], ["Projection version", status.schemaVersion],
      ...entries.map(([key, entry]): [string, string] => [key + " · " + state(entry.evidenceClass), entry.sha256]),
    ]} /></div>
  </details>;
}

export async function QuantConsole({ section, search = {}, runId }: { section: string; search?: Search; runId?: string }) {
  if (!await canReadQuantStatus()) notFound();
  const result = await readQuantStatus();
  const status = "status" in result ? result.status : undefined;
  const run = runId ? details(status)?.runs.find(row => row.id === runId) : undefined;
  if (runId && !run) notFound();
  const pageTitle = sections.find(([key]) => key === section)?.[1] ?? "Instrument evidence";
  return <div className="mx-auto max-w-7xl text-slate-300">
    <header className="mb-6 border-b border-slate-700/70 pb-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-3xl font-semibold tracking-tight text-white">Quant research</h1>
        <span className="text-sm text-slate-400">{status?.authority === "TEST_ONLY" ? "Demo snapshot" : "Private · Read only"}</span>
      </div>
      <dl className="mt-4 flex flex-wrap gap-x-8 gap-y-2 text-sm">
        <div><dt className="text-slate-400">Archived market session</dt><dd className="text-white">{display(status?.marketSession)}</dd></div>
        <div><dt className="text-slate-400">Status generated</dt><dd className="text-white">{dateLabel(status?.asOf)}</dd></div>
        <div><dt className="text-slate-400">Recommendation publishing</dt><dd className="text-amber-300">Locked</dd></div>
      </dl>
    </header>
    {result.state !== "AVAILABLE" && <p role="status" className="mb-5 rounded-lg border border-amber-600/50 bg-amber-950/30 px-4 py-3 text-amber-100">
      {{ EMPTY: "No verified local snapshot is available.", HOSTED_EMPTY: "No verified hosted snapshot is available.",
        INVALID: "The status snapshot failed verification.", STALE: "Archived snapshot. The latest verified figures shown here may be stale." }[result.state]}
    </p>}
    <div className="grid gap-6 lg:grid-cols-[11rem_minmax(0,1fr)]">
      <nav aria-label="Quant sections" className="flex overflow-x-auto rounded-lg border border-slate-800 p-1 lg:sticky lg:top-24 lg:self-start lg:flex-col">
        {sections.map(([key, label]) => <Link key={key} href={key ? `/quant/${key}` : "/quant"}
          aria-current={key === section ? "page" : undefined}
          className={(key === section ? "bg-yellow-500/10 text-yellow-300" : "text-slate-300 hover:bg-slate-800")
            + " shrink-0 rounded px-3 py-2 text-sm font-medium focus-visible:outline-2 focus-visible:outline-yellow-300"}>{label}
        </Link>)}
      </nav>
      <div className="min-w-0 space-y-5">
        <h2 className="text-xl font-semibold text-white">{runId ? "Run provenance" : pageTitle}</h2>
        {run ? <Card heading={run.id}><p className="text-amber-300">Archived diagnostic · Blocked by held valuation</p>
          <Fields items={[["Return basis", state(run.basis)], ["Effective start", run.start], ["Requested end", run.end],
            ["Code SHA", run.codeSha], ["Input manifest", run.manifest], ["Outcome digest", run.outcomeHash]]} />
          <p>Version details for this archived run are {display(null).toLowerCase()}.</p>
          <Link className="text-yellow-300 underline" href="/quant/evidence">Review the CAIRN evidence requirement</Link>
        </Card> : section === "" ? <Overview status={status} />
          : section === "data" ? <Coverage status={status} />
          : section === "evidence" ? <Evidence status={status} search={search} />
          : section === "research" ? <Research status={status} />
          : section === "models" ? <Models status={status} />
          : section === "risk" ? <Risk status={status} />
          : section === "forward" ? <Forward status={status} test={search.cohort === "test"} />
          : section === "operations" ? <Operations status={status} />
          : section === "portfolio" || section === "rankings" ? <Locked />
          : <Card heading="Instrument status"><p className="break-all font-mono">{section}</p><p>Verified instrument metadata is unavailable in this snapshot.</p></Card>}
        {status && <Provenance status={status} />}
      </div>
    </div>
  </div>;
}

function Overview({ status }: { status: Snapshot }) {
  const d = details(status);
  const counts = d?.jointCounts.at(-1);
  const passed = measured(status, "livePassed");
  const failed = measured(status, "liveFailed");
  const filing = status?.coverage.flatMap(row => row.filing === null ? [] : [row.filing]) ?? [];
  const tiles = [
    ["Local tests passed", display(measured(status, "localTestsPassed")), "Local software acceptance"],
    ["Source checks passed", passed != null && failed != null ? `${passed}/${passed + failed}` : display(null), dateLabel(d?.metrics.livePassed?.asOf)],
    ["Complete joint V2 rows", counts ? `${counts.complete}/${counts.eligible}` : display(null), display(counts?.cutoff)],
    ["Peak monthly filings", filing.length ? `${Math.max(...filing).toFixed(2)}%` : display(null), "Across verified monthly cutoff rows"],
    ["Discovery gaps", display(status?.discoveryGaps), "Instrument and cutoff cells"],
    ["Registered real cohorts", display(measured(status, "realCohorts")), "Recorded in this workspace"],
  ];
  return <>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{tiles.map(([label, value, hint]) =>
      <div className={panel} key={label}><p className="text-sm text-slate-300">{label}</p>
        <p className="my-1 text-2xl font-semibold tabular-nums text-white">{value}</p><p className="text-sm text-slate-400">{hint}</p></div>)}</div>
    <Card heading="Readiness gates"><Fields items={[
      ["Software certification", state(status?.implementation)], ["Archived market inputs", state(status?.archiveReadiness)],
      ["Current EOD", state(d?.eod)], ["Historical model admission", state(status?.validationStatus)],
      ["Real forward eligibility", status?.validationStatus === "BLOCKED" ? "blocked" : display(null)],
      ["Recommendation publishing", "Locked"],
    ]} /></Card>
    <Card heading="Blocker inbox"><ul className="divide-y divide-slate-800">
      {[
        ["TIDEWATER · " + state(status?.humanReview), "/quant/evidence", "Complete the independent review before reviewing fallback admission."],
        ["CAIRN · " + (d?.cairnObserved ? "held valuation blocked" : display(null)), "/quant/evidence#cairn", "Verify each consideration leg and evidence availability."],
        ["Filings and shares · " + state(status?.jointMatrix), "/quant/data", "Resolve missing filings and verify event terms before joint certification."],
        ["Market refresh · " + state(d?.eod), "/quant/operations", "Confirm the exchange session using official sources."],
        ["Implementation · " + state(status?.implementation), "/quant/operations", "Check software evidence for the exact revision."],
      ].map(([label, href, action]) => <li className="py-3" key={href}><Link className="text-yellow-300 underline-offset-4 hover:underline" href={href}>{label}</Link>
        <p className="mt-1 text-sm text-slate-400">{action}</p></li>)}
    </ul></Card>
    <Card heading="Controlled operations"><Fields items={[
      ["V2 comparison", d?.fourArmDiagnostic ? "Archived diagnostic completed" : null],
      ["Forward dry run · signal dates", measured(status, "testSignals")], ["Restored synthetic release files", measured(status, "restoredFiles")],
    ]} /></Card>
  </>;
}

function Research({ status }: { status: Snapshot }) {
  const d = details(status);
  return <>
    <Card heading="Research inventory">
      <Fields items={[["Original 2016 baseline", state(status?.validationStatus)], ["Fallback window", state(status?.fallback)]]} />
      {!d?.runs.length ? <p>No diagnostic run metadata is available.</p> : <ul className="divide-y divide-slate-800">
        {d.runs.map(run => <li className="py-3" key={run.id}><Link className="text-yellow-300 underline" href={`/quant/research/${run.id}`}>{run.id}</Link>
          <p>{state(run.basis)} · Diagnostic · Held valuation blocked</p></li>)}
      </ul>}
    </Card>
    <Card heading="Four-arm V2 comparison">
      <p>{d?.fourArmDiagnostic ? "The controlled diagnostic completed. The real V2 decision is pending." : "Controlled run evidence is unavailable."}</p>
      <Fields items={[["Arm A", "Full V1 universe"], ["Arm B", "V1 on the matched universe"], ["Arm C", "Raw V2"], ["Arm D", "Risk-budgeted V2"]]} />
    </Card>
  </>;
}

function Models({ status }: { status: Snapshot }) {
  const d = details(status);
  return <Card heading="Model lifecycle">
    <Fields items={[["V1", status ? `${status.v1Version} · Historical decision ${state(status.validationStatus)}` : null],
      ["V2", status ? `${status.v2Version} · Candidate · Joint data ${state(status.jointMatrix)}` : null],
      ["Elastic Net", "Deferred · Requires a V2 GO decision and a stable point-in-time matrix"],
      ["Promotion", "Locked pending validated results and manual promotion"],
      ["Feature version", status?.featureVersion], ["Accounting version", d?.accountingVersion],
      ["Cost policy", status?.costVersion], ["Risk policy", d?.riskVersion], ["Evidence policy", status?.evidenceVersion]]} />
  </Card>;
}

function Risk({ status }: { status: Snapshot }) {
  const d = details(status);
  const p = d?.riskPolicy;
  const pct = (n: number) => `${Number((n * 100).toFixed(3))}%`;
  return <>
    <Card heading="Configured risk policy">
      {p ? <Fields items={[["Policy version", d?.riskVersion], ["Position cap", pct(p.max_weight)],
        ["Cluster cap", pct(p.max_cluster_weight)], ["ADV participation cap", pct(p.adv_fraction)],
        ["Volatility target", pct(p.target_volatility)], ["Gross exposure cap", pct(p.gross_exposure)],
        ["Turnover penalty", p.turnover_penalty], ["Capacity", "Participation checked against ADV for each order"],
        ["Covariance", "Shrinkage estimate using jointly observed returns"]]} /> : <p>No verified policy snapshot is available.</p>}
    </Card>
    <Card heading="Structural diagnostics"><p>{d?.fourArmDiagnostic
      ? "The archived controlled comparison exercised the risk-budgeted arm." : "No verified structural checks are available."}</p></Card>
  </>;
}

function Forward({ status, test }: { status: Snapshot; test: boolean }) {
  const d = details(status);
  const real = measured(status, "realCohorts");
  return <Card heading={test ? "Test-only cohorts" : "Real cohorts"}>
    <div className="flex gap-4">
      <Link href="/quant/forward" aria-current={!test ? "page" : undefined} className={!test ? "text-yellow-300 underline" : "underline"}>Real</Link>
      <Link href="/quant/forward?cohort=test" aria-current={test ? "page" : undefined} className={test ? "text-yellow-300 underline" : "underline"}>Test only</Link>
    </div>
    {test ? <Fields items={[["Scope", "Test only"], ["Observation cutoff", d?.metrics.testSignals?.asOf],
      ["Signal dates", measured(status, "testSignals")], ["Shadow observations", measured(status, "shadowObservations")],
      ["Matured 21-session outcomes", measured(status, "matured21")], ["Matured 63-session outcomes", measured(status, "matured63")]]} />
      : <p>{real === 0 ? "No eligible real cohorts." : real == null ? "Real cohort evidence is unavailable."
        : `${display(real)} registered cohorts. Eligibility is locked pending verification.`}</p>}
  </Card>;
}

function Operations({ status }: { status: Snapshot }) {
  const d = details(status);
  return <>
    <Card heading="Software and refresh">
      <Fields items={[["Local tests passed", measured(status, "localTestsPassed")], ["Local acceptance time", dateLabel(d?.metrics.localTestsPassed?.asOf)],
        ["Source revision", status?.gitCommit], ["Certified revision", d?.certifiedSha], ["Current EOD", state(d?.eod)],
        ["Windows scheduling", state(d?.scheduler)], ["Last successful scheduled job", null],
        ["Hosted status sync", "Requires separate configuration and verification"]]} />
    </Card>
    <Card heading="Monitoring and incidents"><Fields items={[["Open real incidents", status?.openIncidents],
      ["Open injected test incidents", measured(status, "testIncidents")], ["Test observation cutoff", d?.metrics.testIncidents?.asOf],
      ["Restored synthetic release files", measured(status, "restoredFiles")]]} /></Card>
  </>;
}

function Locked() {
  return <Card heading="Access locked"><p>Access requires a manually promoted champion, eligible current data, verified risk limits and publication approval.</p>
    <Link className="text-yellow-300 underline" href="/quant/models">View model and promotion gates</Link></Card>;
}
