import { SlicePlaceholder } from "@/components/ecom/SlicePlaceholder";

export default function BrandPage() {
  return (
    <SlicePlaceholder
      title="Brand"
      subtitle="Markdown vault that the agents read"
      slice="Build slice 5"
      bullets={[
        "Obsidian-style markdown editor writing into the vault.",
        "Embedding index (pgvector) powers retrieval for Chat and the CS agent.",
        "Shipping and privacy policy docs feed the WISMO answer.",
      ]}
    />
  );
}
