import { notFound, redirect } from "next/navigation";
import { QuantConsole, sections } from "../console";
import { canReadQuantStatus } from "@/lib/quant/status-server";
import type { Search } from "../evidence-views";

export const dynamic = "force-dynamic";

export default async function Page({ params, searchParams }: {
  params: Promise<{ section: string }>;
  searchParams: Promise<Search>;
}) {
  const { section } = await params;
  if (section === "coverage") {
    if (!await canReadQuantStatus()) notFound();
    redirect("/quant/data");
  }
  if (!sections.some(([key]) => key && key === section)
    && !/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(section)) notFound();
  return <QuantConsole section={section} search={await searchParams} />;
}
