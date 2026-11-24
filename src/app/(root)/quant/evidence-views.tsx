import Link from "next/link";
import type { CoverageRow } from "@/lib/quant/status-contract";
import { Card, Fields, dateLabel, details, display, measured, state, type Snapshot } from "./presentation";

export type Search = Record<string, string | string[] | undefined>;
const series = [
  ["filing", "Usable filings", "bg-sky-400"], ["ceiling", "Filing ceiling", "bg-slate-500"],
  ["joint", "Joint rows", "bg-teal-400"], ["filingTop100", "Usable filings", "bg-sky-400"],
  ["ceilingTop100", "Filing ceiling", "bg-slate-500"], ["jointTop100", "Joint rows", "bg-teal-400"],
] as const;
const percent = (value?: number | null) => value == null ? display(null) : `${value.toFixed(2)}%`;

function Peak({ rows }: { rows: CoverageRow[] }) {
  const best = (key: "filing" | "ceiling" | "ceilingTop100") =>
    rows.reduce<CoverageRow | undefined>((max, row) => row[key] !== null && (!max || row[key] > (max[key] ?? -1)) ? row : max, undefined);
  const filing = best("filing");
  const ceiling = best("ceiling");
  const top = best("ceilingTop100");
  const label = (row: CoverageRow | undefined, key: "filing" | "ceiling" | "ceilingTop100") =>
    row?.[key] == null ? display(null) : `${percent(row[key])} · ${row.cutoff}`;
  return <Fields items={[["Peak usable filing coverage", label(filing, "filing")],
    ["Best overall filing ceiling", label(ceiling, "ceiling")],
    ["Top-100 ceiling at the best overall cutoff", label(ceiling, "ceilingTop100")],
    ["Independent top-100 ceiling", label(top, "ceilingTop100")]]} />;
}

function CoverageChart({ rows, top }: { rows: CoverageRow[]; top: boolean }) {
  const selected = top ? series.slice(3) : series.slice(0, 3);
  const threshold = top ? 90 : 80;
  return <figure className="min-w-0">
    <figcaption className="mb-3 font-medium text-slate-200">{top ? "Historical top 100 by liquidity" : "Eligible universe"}</figcaption>
    <div className="relative">
      <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 z-10 border-t border-dashed border-amber-400/90" style={{ bottom: threshold + "%" }} />
      <div className="flex h-36 items-end gap-px border-b border-slate-700" aria-hidden="true">
        {rows.map(row => <div key={row.cutoff} className="flex h-full min-w-0 flex-1 items-end gap-px">
          {selected.map(([key, name, color]) => <div key={key} className={"min-w-0 flex-1 " + color}
            style={{ height: row[key] == null ? 0 : `max(2px, ${row[key]}%)` }} title={`${row.cutoff}: ${name} ${percent(row[key])}`} />)}
        </div>)}
      </div>
    </div>
    <div className="mt-2 flex justify-between gap-2 text-xs text-slate-400"><span>{rows[0]?.cutoff}</span><span>{rows.at(-1)?.cutoff}</span></div>
    <p className="mt-2 text-sm text-amber-200">{threshold}% certification threshold</p>
  </figure>;
}

function Table({ headings, rows, label }: { headings: string[]; rows: React.ReactNode[][]; label: string }) {
  return <div className="overflow-x-auto" tabIndex={0} role="region" aria-label={label}>
    <table className="w-full text-left text-sm">
      <thead><tr className="border-b border-slate-700">{headings.map(heading =>
        <th className="px-2 py-3 font-semibold text-slate-200" scope="col" key={heading}>{heading}</th>)}</tr></thead>
      <tbody className="divide-y divide-slate-800">{rows.map((row, index) =>
        <tr key={index}>{row.map((value, column) => column === 0
          ? <th scope="row" className="whitespace-nowrap px-2 py-3 font-medium text-white" key={column}>{value}</th>
          : <td className="min-w-24 px-2 py-3 tabular-nums" key={column}>{value}</td>)}</tr>)}</tbody>
    </table>
  </div>;
}

export function Coverage({ status }: { status: Snapshot }) {
  const d = details(status);
  const rows = status?.coverage ?? [];
  return <>
    <Card heading="Filing and joint coverage">
      <Peak rows={rows} />
      <Fields items={[["Continuous 12-month certification", d?.continuousJoint ? "Verified" : state(status?.jointMatrix)],
        ["Discovery planning targets", "85% overall and 95% for the historical top 100"]]} />
      {rows.length > 0 ? <>
        <div className="flex flex-wrap gap-4 text-sm">{series.slice(0, 3).map(([key, name, color]) =>
          <span className="flex items-center gap-2" key={key}><span aria-hidden="true" className={"size-2.5 rounded-sm " + color} />{name}</span>)}</div>
        <div className="grid gap-5 sm:grid-cols-2"><CoverageChart rows={rows} top={false} /><CoverageChart rows={rows} top /></div>
        <details className="mt-4">
          <summary className="cursor-pointer text-yellow-300">View coverage values by cutoff</summary>
          <Table label="Filing, share and joint coverage by cutoff"
            headings={["Cutoff", "Filings", "Top-100 filings", "Ceiling", "Top-100 ceiling", "Shares", "Top-100 shares", "Joint", "Joint top 100"]}
            rows={[...rows].reverse().map(row => [row.cutoff, ...(["filing", "filingTop100", "ceiling", "ceilingTop100",
              "shares", "sharesTop100", "joint", "jointTop100"] as const).map(key => percent(row[key]))])} />
        </details>
      </> : <p>Coverage rows are unavailable.</p>}
    </Card>
    <Card heading="Joint row eligibility">
      {d?.jointCounts.length ? <Table label="Complete rows and eligible denominators" headings={["Cutoff", "Complete / eligible", "Top-100 complete / eligible", "Verified Value missing"]}
        rows={d.jointCounts.map(r => [r.cutoff, `${r.complete} / ${r.eligible}`, `${r.topComplete} / ${r.topEligible}`, display(r.valueMissing)])} />
        : <p>Joint numerators and denominators are unavailable.</p>}
      {d?.jointCounts.some(r => r.eligible > 0 && r.complete === 0) && <p>Details of missing fields and share evidence are in the evidence queue.</p>}
    </Card>
    <Card heading="Source checks">
      <Fields items={[["Latest archived market session", status?.marketSession],
        ["Current EOD readiness", state(d?.eod)], ["Latest source smoke report time", dateLabel(d?.metrics.livePassed?.asOf)],
        ["Latest source checks passed", measured(status, "livePassed")], ["Latest source checks failed", measured(status, "liveFailed")],
        ["Earlier source smoke time", dateLabel(d?.metrics.priorLivePassed?.asOf)],
        ["Earlier source checks passed", measured(status, "priorLivePassed")], ["Earlier source checks failed", measured(status, "priorLiveFailed")]]} />
      {d?.probes.length ? <Table label="Archived source probes" headings={["Route", "Probe time", "HTTP status", "State"]}
        rows={d.probes.map(p => [p.route, dateLabel(p.asOf), display(p.httpStatus), state(p.state)])} />
        : <p>Route-level source checks are unavailable.</p>}
    </Card>
    <Card heading="Discovery and repair">
      <Fields items={[["Missing discovery cells", measured(status, "discoveryCells") ?? status?.discoveryGaps],
        ["Instruments with discovery gaps", measured(status, "discoveryInstruments")],
        ["Broader usability failures · instrument and cutoff cells", measured(status, "usabilityCells")],
        ["Pilot cells selected", measured(status, "pilotCells")], ["Pilot documents admitted", measured(status, "admittedDocuments")],
        ["Discovery cells closed in the pilot", measured(status, "verifiedRepairs")], ["Zero-marginal candidate count", null]]} />
      <Link className="text-yellow-300 underline" href="/quant/evidence#queues">Open the evidence queues</Link>
    </Card>
  </>;
}

const PAGE_SIZE = 12;
function Queue({ status, search }: { status: Snapshot; search: Search }) {
  const d = details(status);
  const isCapital = search.queue !== "filings";
  const filter = typeof search.filter === "string" ? search.filter : "";
  const capital = d?.capitalQueue.filter(row => !filter || row.state === filter) ?? [];
  const filings = d?.filingQueue.filter(row => filter !== "top100" || row.top100) ?? [];
  const rowCount = isCapital ? capital.length : filings.length;
  const pages = Math.max(1, Math.ceil(rowCount / PAGE_SIZE));
  const requested = typeof search.page === "string" && /^\d{1,5}$/.test(search.page) ? Number(search.page) : 1;
  const page = Math.min(pages, Math.max(1, requested));
  const start = (page - 1) * PAGE_SIZE;
  const href = (index: number) => `?queue=${isCapital ? "capital" : "filings"}&filter=${encodeURIComponent(filter)}&page=${index}#queues`;
  return <Card heading="Evidence queues">
    <div id="queues" className="flex flex-wrap gap-4">
      <Link href="?queue=capital#queues" aria-current={isCapital ? "page" : undefined} className={isCapital ? "text-yellow-300 underline" : "underline"}>Capital events</Link>
      <Link href="?queue=filings#queues" aria-current={!isCapital ? "page" : undefined} className={!isCapital ? "text-yellow-300 underline" : "underline"}>Filing discovery</Link>
    </div>
    <form action="/quant/evidence#queues" className="flex flex-wrap items-end gap-3">
      <input type="hidden" name="queue" value={isCapital ? "capital" : "filings"} />
      <label className="grid gap-1 text-sm">{isCapital ? "Verification state" : "Universe"}
        <select name="filter" defaultValue={filter} className="rounded border border-slate-600 bg-slate-900 px-3 py-2">
          <option value="">All rows</option>
          {(isCapital ? ["NEEDS_REVIEW", "CANDIDATE", "TERMS_VERIFIED", "DATES_VERIFIED", "VERIFIED_COMPLETE", "REJECTED"] : ["top100"])
            .map(value => <option value={value} key={value}>{value === "top100" ? "Historical top 100" : state(value)}</option>)}
        </select>
      </label>
      <button className="rounded border border-slate-600 px-3 py-2 text-sm hover:bg-slate-800" type="submit">Apply filter</button>
    </form>
    <p className="text-sm text-slate-400">{display(rowCount)} rows in the exported sample and filter. Total workload: {display(isCapital ? status?.capitalCandidates : status?.discoveryGaps)}.</p>
    {rowCount === 0 ? <p>No rows available for this filter.</p> : isCapital
      ? <Table label="Capital event sample" headings={["Event", "Instrument", "State", "Effective", "Known", "Source digest", "Lineage", "Missing terms"]}
        rows={capital.slice(start, start + PAGE_SIZE).map(r => [state(r.event), r.instrument, state(r.state), display(r.effective),
          dateLabel(r.known), <span key="digest" className="break-all">{display(r.source)}</span>, r.lineage ? "Recorded" : "Missing",
          r.missing.length ? r.missing.map(state).join(", ") : display(null)])} />
      : <Table label="Filing discovery sample" headings={["Instrument", "Cutoff", "Required period", "Latest known by", "Source lead"]}
        rows={filings.slice(start, start + PAGE_SIZE).map(r => [r.symbol, r.cutoff, display(r.period), dateLabel(r.knownBy),
          r.candidate ? "Candidate requires point-in-time validation" : "Discovery required"])} />}
    {pages > 1 && <nav className="flex flex-wrap items-center gap-4 text-sm" aria-label="Evidence queue pages">
      {page > 1 && <Link href={href(page - 1)} className="text-yellow-300 underline">Previous</Link>}
      <span>Page {page} of {pages}</span>
      {page < pages && <Link href={href(page + 1)} className="text-yellow-300 underline">Next</Link>}
    </nav>}
  </Card>;
}

export function Evidence({ status, search }: { status: Snapshot; search: Search }) {
  const d = details(status);
  return <>
    <Card heading="TIDEWATER · 2016">
      <Fields items={[["Automated search", d?.tidewaterExhausted ? "Evidence exhausted · unresolved" : null],
        ["Independent review", state(status?.humanReview)], ["Fallback admission", state(status?.fallback)],
        ["Prepared start", d?.fallbackStart], ["Canonical audit digest", d?.tidewaterAudit]]} />
      <p>Use the local TIDEWATER human-review packet and reviewed CLI workflow. Fallback admission requires a distinct reviewed decision.</p>
    </Card>
    <div id="cairn"><Card heading="CAIRN · held valuation">
      <Fields items={[["Archived diagnostic block date", d?.cairnObserved], ["Scope", d?.cairnObserved ? "Archived diagnostic" : null]]} />
      {d?.cairnObserved && <p>Evidence is required for equity and preference consideration, cash and dividends, credit and listing dates, and instrument lineage.</p>}
      <Link href="/quant/research" className="text-yellow-300 underline">View archived run records</Link>
    </Card></div>
    <Queue status={status} search={search} />
  </>;
}
