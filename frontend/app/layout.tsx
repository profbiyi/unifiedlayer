import type { Metadata } from "next";
import { Inter, Bricolage_Grotesque } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as HotToaster } from "react-hot-toast";
import { QueryProvider } from "@/components/query-provider";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  fallback: ["system-ui", "arial"],
});

// Display font for headings — gives the brand a voice of its own instead of
// the default all-Inter look. Exposed as `font-display` via tailwind config.
const bricolage = Bricolage_Grotesque({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-display",
  fallback: ["system-ui", "arial"],
});

export const metadata: Metadata = {
  title: "UnifiedLayer",
  description: "Cloud-based data integration and analytics platform for SMEs. Turn fragmented data into clarity.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} ${bricolage.variable}`}>
        {/* Default to the bright theme — first impressions (public site,
            jury, prospects) should never depend on the visitor's OS setting.
            Users who explicitly pick dark keep their choice. */}
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem
          disableTransitionOnChange
        >
          <QueryProvider>
            {children}
            <Toaster />
            <HotToaster position="top-right" />
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
