import type { Metadata, Viewport } from "next";
import "./globals.css";
import SWRegister from "./sw-register";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "IndieAid — Help India's Stray Dogs",
  description:
    "AI-powered assistant to assess stray dog conditions, provide first aid guidance, and connect you with shelters and vets in India.",
  manifest: "/manifest.json",
  icons: { icon: "/logo-192.png", apple: "/logo-192.png" },
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
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
