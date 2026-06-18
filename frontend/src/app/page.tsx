import { redirect } from "next/navigation";

/**
 * Ecom-OS is the only surface. The legacy marketing homepage is deprecated — the
 * root redirects straight into the operations dashboard. Auth is handled globally
 * by AuthProvider (local-auth login when there's no token).
 */
export default function Page() {
  redirect("/overview");
}
