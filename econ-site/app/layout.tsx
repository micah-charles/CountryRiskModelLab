import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Econ Research Hub",
  description: "Private snapshots and research views for country and market risk.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
