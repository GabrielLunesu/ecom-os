import { SlicePlaceholder } from "@/components/ecom/SlicePlaceholder";

export default function AnalyticsPage() {
  return (
    <SlicePlaceholder
      title="Analytics"
      subtitle="Per-store and aggregate · date ranges · comparison · funnel"
      slice="Build slice 3"
      bullets={[
        "Everything Shopify exposes, per store and aggregated.",
        "Date-range selection with store-vs-store comparison.",
        "Conversion funnel and order-derived KPIs (revenue, AOV, orders).",
      ]}
    />
  );
}
