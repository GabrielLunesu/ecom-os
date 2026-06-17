import { SlicePlaceholder } from "@/components/ecom/SlicePlaceholder";

export default function ChatPage() {
  return (
    <SlicePlaceholder
      title="Chat"
      subtitle="Read-only copilot over Shopify (all stores) + the brand vault"
      slice="Build slice 6"
      bullets={[
        "Ask questions across every connected store and the vault.",
        "Strictly read-only — no writes, a separate trust surface from tickets.",
        "Cites sources from Shopify data and vault documents.",
      ]}
    />
  );
}
