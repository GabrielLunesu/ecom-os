import "./globals.css";

import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Inter } from "next/font/google";

import { AuthProvider } from "@/components/providers/AuthProvider";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { GlobalLoader } from "@/components/ui/global-loader";

export const metadata: Metadata = {
  title: "Ecom-OS",
  description: "Operations command center for the brand.",
};

// Single typeface for the whole product: Inter, with tabular figures enabled
// globally via globals.css. Tracking is tightened on headings (design tokens).
const sans = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
  weight: ["400", "500", "600", "700"],
});

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        className={`${sans.variable} min-h-screen bg-app text-strong antialiased`}
      >
        <AuthProvider>
          <QueryProvider>
            <GlobalLoader />
            {children}
          </QueryProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
