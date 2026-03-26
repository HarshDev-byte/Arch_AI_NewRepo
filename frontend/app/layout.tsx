import "./globals.css";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Providers from "./providers";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "ArchAI — AI Architectural Design in Minutes",
  description:
    "ArchAI uses 8 specialised AI agents to generate unique building designs, floor plans, cost estimates and 3D models from a map pin. Free, fast, FSI-compliant.",
  keywords: ["AI architecture", "floor plan generator", "LangGraph", "India construction", "3D building"],
  openGraph: {
    title: "ArchAI — AI Architectural Design",
    description: "8 AI agents. 5 unique designs. 10 minutes.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className={`${inter.className} bg-[#080C14] text-white antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}