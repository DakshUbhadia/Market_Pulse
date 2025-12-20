import TradingLoader from "@/components/ui/TradingLoader";

export default function Loading() {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md">
      <div className="w-[220px] max-w-[70vw]">
        <TradingLoader />
      </div>
    </div>
  );
}
