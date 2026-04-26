import type { Metadata, Viewport } from "next";
import "./globals.css";
import SWRegister from "./sw-register";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "IndieAid - Grounded AI Help for Pets and Community Animals",
  description:
    "AI-powered guidance for pets and community animals: assess condition from a photo, get grounded first-aid steps, and find verified help resources.",
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
