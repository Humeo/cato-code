import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CatoCode — Autonomous Code Maintainer",
  description: "AI-powered autonomous GitHub repository maintenance",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 min-h-screen font-mono antialiased">
        {children}
      </body>
    </html>
  );
}
