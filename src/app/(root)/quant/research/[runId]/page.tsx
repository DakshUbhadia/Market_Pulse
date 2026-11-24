import { QuantConsole } from "../../console";

export const dynamic = "force-dynamic";

export default async function Page({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  return <QuantConsole section="research" runId={runId} />;
}
