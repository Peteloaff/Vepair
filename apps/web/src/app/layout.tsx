import type { Metadata, Viewport } from "next";
import { Albert_Sans, Geist_Mono, Outfit } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { ThemeProvider } from "@/lib/theme-context";
import { TopNav } from "@/components/TopNav";
import { NdaGate } from "@/components/NdaGate";

// Runs before hydration (first child of <head>, blocking) so the page never paints the wrong
// theme and then flips -- must resolve identically to ThemeProvider's own resolveAndApply
// (lib/theme-context.tsx): same "vepair_theme" key, same system-preference fallback.
const NO_FLASH_THEME_SCRIPT = `try{var t=localStorage.getItem("vepair_theme");var d=t==="dark"||((!t||t==="system")&&window.matchMedia("(prefers-color-scheme: dark)").matches);if(d)document.documentElement.classList.add("dark");}catch(e){}`;

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
});

const albertSans = Albert_Sans({
  variable: "--font-albert",
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
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#eef4fa" },
    { media: "(prefers-color-scheme: dark)", color: "#07111d" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${outfit.variable} ${albertSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: NO_FLASH_THEME_SCRIPT }} />
      </head>
      <body className="min-h-full flex flex-col bg-canvas text-text">
        <ThemeProvider>
          <AuthProvider>
            <TopNav />
            <NdaGate>{children}</NdaGate>
            <footer className="border-t border-border px-6 py-4 text-center text-xs text-text-faint">
              <Link href="/terms" className="hover:text-text-dim">
                Terms of Service
              </Link>
            </footer>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
