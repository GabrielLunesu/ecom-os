import { PageHeader } from "./PageHeader";

/** Polished placeholder for pages whose data/logic lands in a later build
 * slice. Keeps the shell fully navigable while the design system is in place. */
export function SlicePlaceholder({
  title,
  subtitle,
  slice,
  bullets,
}: {
  title: string;
  subtitle: string;
  slice: string;
  bullets: string[];
}) {
  return (
    <div>
      <PageHeader title={title} subtitle={subtitle} />
      <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-6 shadow-card">
        <span className="inline-flex items-center rounded-full bg-[color:var(--accent-soft)] px-2.5 py-1 text-xs font-medium text-[color:var(--accent)]">
          {slice}
        </span>
        <ul className="mt-4 space-y-2">
          {bullets.map((b) => (
            <li key={b} className="flex items-start gap-2.5 text-sm text-muted">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[color:var(--border-strong)]" />
              {b}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
