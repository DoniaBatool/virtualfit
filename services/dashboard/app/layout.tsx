import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VirtualFit — AI Virtual Try-On",
  description: "Try on clothes with AI: IDM-VTON + SAM2 + Quantum Search",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
