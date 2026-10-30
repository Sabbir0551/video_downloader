import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AnyStream - High-Performance Video Downloader",
  description: "Secure, high-performance web media downloader platform.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full antialiased dark">
      <body className="min-h-full flex flex-col bg-slate-950 text-slate-100 font-sans">
        {children}
      </body>
    </html>
  );
}
