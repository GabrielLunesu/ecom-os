import { SlicePlaceholder } from "@/components/ecom/SlicePlaceholder";

export default function CustomerServicePage() {
  return (
    <SlicePlaceholder
      title="Customer Service"
      subtitle="Overview · Tickets board · Setup"
      slice="Build slices 7–11"
      bullets={[
        "Tickets Kanban: new → auto_handling → awaiting_customer → needs_rep → resolved.",
        "Sticky escalation: once a rep is needed, replies never re-trigger automation.",
        "CS agent handles read + discounts; refunds are a separate approval-gated path.",
      ]}
    />
  );
}
