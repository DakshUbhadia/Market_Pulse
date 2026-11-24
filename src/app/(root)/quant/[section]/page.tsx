import { notFound } from "next/navigation";
import { QuantConsole } from "../console";

export const dynamic = "force-dynamic";

export default async function Page({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  if (!["coverage", "research", "portfolio"].includes(section)
    && !/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(section)) notFound();
  return <QuantConsole section={section} />;
}
