import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { TopNav } from "@/components/TopNav";
import { NdaGate } from "@/components/NdaGate";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "VepAIr",
  description: "AI-assisted vocal recovery, conditioning, and performance platform.",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    title: "VepAIr",
  },
};

export const viewport: Viewport = {
  themeColor: "#0a0a0a",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col bg-neutral-950 text-neutral-100">
        <AuthProvider>
          <TopNav />
          <NdaGate>{children}</NdaGate>
          <footer className="border-t border-neutral-800 px-6 py-4 text-center text-xs text-neutral-600">
            <Link href="/terms" className="hover:text-neutral-400">
              Terms of Service
            </Link>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
