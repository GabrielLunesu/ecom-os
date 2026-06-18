import { NextResponse } from "next/server";
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

import { isLikelyValidClerkPublishableKey } from "@/auth/clerkKey";
import { AuthMode } from "@/auth/mode";

const isClerkEnabled = () =>
  process.env.NEXT_PUBLIC_AUTH_MODE !== AuthMode.Local &&
  isLikelyValidClerkPublishableKey(
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY,
  );

// Public routes include home and sign-in paths to avoid redirect loops.
const isPublicRoute = createRouteMatcher(["/", "/sign-in(.*)", "/sign-up(.*)"]);

function isClerkInternalPath(pathname: string): boolean {
  // Clerk may hit these paths for internal auth/session refresh flows.
  return pathname.startsWith("/_clerk") || pathname.startsWith("/v1/");
}

/**
 * Ecom-OS is the only surface. Legacy Mission Control routes are deprecated — each
 * one bounces to its Ecom-OS equivalent (runs in both auth modes, before auth).
 */
const LEGACY_REDIRECTS: Record<string, string> = {
  "/dashboard": "/overview",
  "/boards": "/tasks",
  "/board-groups": "/tasks",
  "/approvals": "/cs",
  "/activity": "/cs",
  "/gateways": "/settings",
  "/skills": "/settings",
  "/tags": "/settings",
  "/custom-fields": "/settings",
  "/organization": "/settings",
};

function legacyRedirect(req: Request): NextResponse | null {
  const url = new URL(req.url);
  for (const [legacy, target] of Object.entries(LEGACY_REDIRECTS)) {
    if (url.pathname === legacy || url.pathname.startsWith(`${legacy}/`)) {
      url.pathname = target;
      return NextResponse.redirect(url);
    }
  }
  return null;
}

function requestOrigin(req: Request): string {
  const forwardedProto = req.headers.get("x-forwarded-proto");
  const forwardedHost = req.headers.get("x-forwarded-host");
  const host = forwardedHost ?? req.headers.get("host");
  const proto = forwardedProto ?? "http";
  if (host) return `${proto}://${host}`;
  return new URL(req.url).origin;
}

function returnBackUrlFor(req: Request): string {
  const { pathname, search, hash } = new URL(req.url);
  return `${requestOrigin(req)}${pathname}${search}${hash}`;
}

export default isClerkEnabled()
  ? clerkMiddleware(async (auth, req) => {
      const legacy = legacyRedirect(req);
      if (legacy) return legacy;
      if (isClerkInternalPath(new URL(req.url).pathname)) {
        return NextResponse.next();
      }
      if (isPublicRoute(req)) return NextResponse.next();

      // In middleware, `auth()` resolves to a session/auth context (Promise in current typings).
      // Use redirectToSignIn() (instead of protect()) for unauthenticated requests.
      const { userId, redirectToSignIn } = await auth();
      if (!userId) {
        return redirectToSignIn({ returnBackUrl: returnBackUrlFor(req) });
      }

      return NextResponse.next();
    })
  : (req: Request) => legacyRedirect(req) ?? NextResponse.next();

export const config = {
  matcher: [
    "/((?!_next|_clerk|v1|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
