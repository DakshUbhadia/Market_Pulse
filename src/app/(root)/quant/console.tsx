import Link from "next/link";
import { notFound } from "next/navigation";
import { canReadQuantStatus, readQuantStatus } from "@/lib/quant/status-server";
import type { CoverageRow, QuantStatus } from "@/lib/quant/status-contract";

const tabs = [
  ["/quant", "Overview"], ["/quant/coverage", "Coverage"],
  ["/quant/research", "Research"], ["/quant/portfolio", "Portfolio"],
] as const;

const panel = "rounded-lg border border-slate-700/70 bg-slate-900/70 p-5";
const heading = "text-lg font-semibold text-slate-100";
const number = new Intl.NumberFormat("en-IN");
const snapshotTime = new Intl.DateTimeFormat("en-IN", {
  timeZone: "Asia/Kolkata", year: "numeric", month: "short", day: "numeric",
  hour: "numeric", minute: "2-digit", timeZoneName: "short",
});

function count(value: number | null | undefined) {
  return value == null ? "Unknown" : number.format(value);
}

function displayStatus(value: string | undefined) {
  return value ? value.replaceAll("_", " ").toLowerCase() : "unknown";
}

export async function QuantConsole({ section }: { section: string }) {
  if (!await canReadQuantStatus()) notFound();
  const result = await readQuantStatus();
  const status = "status" in result ? result.status : undefined;
  const title = tabs.find(([href]) => href === (section ? `/quant/${section}` : "/quant"))?.[1] ?? "Instrument";
  return (
    <div className="mx-auto max-w-6xl space-y-6 text-base text-slate-300">
      <header className="space-y-4 border-b border-slate-700 pb-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-100">Quant research</h1>
          <span className="rounded border border-slate-600 px-3 py-1 text-sm text-slate-300">
            {status?.authority === "TEST_ONLY" ? "Test fixture" : "Private status"}
          </span>
        </div>
        <nav aria-label="Quant research" className="flex flex-wrap gap-x-5 gap-y-3 text-sm">
          {tabs.map(([href, label]) => (
            <Link key={href} href={href} aria-current={title === label ? "page" : undefined}
              className={title === label ? "font-semibold text-yellow-400" : "text-slate-300 hover:text-white"}>
              {label}
            </Link>
          ))}
        </nav>
      </header>

      {result.state !== "AVAILABLE" && (
        <p role="status" className="rounded border border-yellow-600/50 bg-yellow-950/30 px-4 py-3 text-yellow-100">
          {result.state === "EMPTY" && "No status snapshot has been loaded."}
          {result.state === "INVALID" && "The status snapshot could not be verified."}
          {result.state === "STALE" && "This status snapshot is older than 48 hours. Figures below are archived."}
        </p>
      )}

      {section === "coverage" ? <Coverage rows={status?.coverage ?? []} />
        : section === "research" ? <Research status={status} />
        : section === "portfolio" ? <Portfolio />
        : section ? <Instrument id={section} />
        : <Overview status={status} />}
      {status && (
        <p className="break-words border-t border-slate-700 pt-4 text-sm text-slate-400">
          Snapshot generated <time dateTime={status.asOf}>{snapshotTime.format(new Date(status.asOf))}</time>
        </p>
      )}
    </div>
  );
}

function Overview({ status }: { status?: QuantStatus }) {
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-3">
        {[
          ["Certified market session", status?.marketSession ?? "Unknown"],
          ["Missing filing discoveries", count(status?.discoveryGaps)],
          ["Open incidents", count(status?.openIncidents)],
        ].map(([label, value]) => (
          <div key={label} className={panel}>
            <p className="text-sm text-slate-300">{label}</p>
            <p className="mt-2 text-2xl font-semibold tabular-nums text-white">{value}</p>
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Research status={status} />
        <section className={panel}>
          <h2 className={heading}>Evidence workload</h2>
          <p className="mt-3 text-slate-300">Capital-event candidates under review</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-white">{count(status?.capitalCandidates)}</p>
          <Link href="/quant/coverage" className="mt-4 inline-block text-yellow-400 underline underline-offset-4">View monthly coverage</Link>
        </section>
      </div>
    </>
  );
}

function Research({ status }: { status?: QuantStatus }) {
  const gates = [
    ["TIDEWATER human review", displayStatus(status?.humanReview)],
    ["Fallback evaluation window", displayStatus(status?.fallback)],
    ["Code certification", displayStatus(status?.implementation)],
    ["Historical market archive", displayStatus(status?.archiveReadiness)],
    ["Filing acquisition", displayStatus(status?.filingSources)],
    ["Joint V2 data interval", displayStatus(status?.jointMatrix)],
    ["Historical evidence", displayStatus(status?.validationStatus)],
    ["Recommendation publishing", "disabled"],
  ];
  return (
    <section className={panel}>
      <h2 className={heading}>Research gates</h2>
      <dl className="mt-3 divide-y divide-slate-800">
        {gates.map(([label, value]) => (
          <div key={label} className="flex flex-wrap justify-between gap-x-4 gap-y-1 py-2">
            <dt>{label}</dt><dd className="font-medium capitalize text-slate-100">{value}</dd>
          </div>
        ))}
        {status && [
          ["Models", `V1 ${status.v1Version} · V2 ${status.v2Version}`],
          ["Policy versions", `Features ${status.featureVersion} · Costs ${status.costVersion} · Evidence ${status.evidenceVersion}`],
          ["Code SHA", status.gitCommit],
          ["Snapshot ID", status.runId],
          ["Input manifest SHA-256", status.inputManifestHash ?? "Unknown"],
        ].map(([label, value]) => (
          <div key={label} className="py-2">
            <dt className="text-sm">{label}</dt><dd className="break-all text-sm text-slate-100">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

const series = [
  ["filing", "Filings"], ["filingTop100", "Filings top 100"],
  ["ceiling", "Filing ceiling"], ["ceilingTop100", "Ceiling top 100"],
  ["shares", "Shares"], ["sharesTop100", "Shares top 100"],
  ["joint", "Joint matrix"], ["jointTop100", "Joint top 100"],
] as const;

function Coverage({ rows }: { rows: CoverageRow[] }) {
  return (
    <section className={panel}>
      <h2 className={heading}>Monthly evidence coverage</h2>
      <p className="mt-2 text-sm">Thresholds are 80% of eligible instruments and 90% of the historical top 100 by liquidity.</p>
      {rows.length === 0 ? <p className="mt-4">No measured coverage is available.</p> : (
        <div className="mt-4 overflow-x-auto" tabIndex={0} aria-label="Scrollable monthly coverage table">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-slate-200">
                <th scope="col" className="p-2">Cutoff</th>
                {series.map(([key, label]) => <th key={key} scope="col" className="min-w-24 p-2">{label}</th>)}
              </tr>
            </thead>
            <tbody>
              {[...rows].reverse().map(row => (
                <tr key={row.cutoff} className="border-b border-slate-800">
                  <th scope="row" className="whitespace-nowrap p-2 font-medium text-slate-100">{row.cutoff}</th>
                  {series.map(([key]) => {
                    const value = row[key];
                    const threshold = key.endsWith("Top100") ? 90 : 80;
                    const surface = value == null ? "text-slate-400" : value >= threshold
                      ? "bg-emerald-950 text-emerald-200" : "bg-slate-800/70 text-slate-200";
                    return <td key={key} className={`p-2 tabular-nums ${surface}`}>{value == null ? "Unknown" : `${value.toFixed(1)}%`}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function Portfolio() {
  return (
    <section className={panel}>
      <h2 className={heading}>Portfolio constraints</h2>
      <p className="mt-3">Example only. A ₹10 lakh research portfolio with ₹8 lakh allocated to model inputs retains ₹2 lakh in cash.</p>
      <p className="mt-3">Research portfolios use whole shares, long-only cash equities and liquidity caps. The model carries unfilled allocations as cash.</p>
    </section>
  );
}

function Instrument({ id }: { id: string }) {
  return (
    <section className={panel}>
      <h2 className={heading}>Instrument evidence</h2>
      <p className="mt-3 break-all font-mono text-sm text-slate-100">{id}</p>
      <p className="mt-3">Identity, source age and eligibility are unknown for this identifier in the loaded status snapshot.</p>
    </section>
  );
}
