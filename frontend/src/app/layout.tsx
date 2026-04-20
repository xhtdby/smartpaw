import type { Metadata, Viewport } from "next";
import "./globals.css";
import SWRegister from "./sw-register";

export const metadata: Metadata = {
  title: "SmartPaw — Help Mumbai's Stray Dogs",
  description:
    "AI-powered assistant to assess stray dog conditions, provide first aid guidance, and connect you with shelters and vets in Mumbai.",
  manifest: "/manifest.json",
  icons: { icon: "/icon-192.svg", apple: "/icon-192.svg" },
};

export const viewport: Viewport = {
  themeColor: "#e87d1e",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="paw-bg min-h-screen">
        <SWRegister />
        {children}
      </body>
    </html>
  );
}
