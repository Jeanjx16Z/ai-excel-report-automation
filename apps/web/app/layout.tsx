import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./styles.css";

export const metadata: Metadata = {
  title: "Laporan Biaya Pertambangan | Excel ke PDF",
  description: "Demo lokal: Excel sintetis menjadi KPI biaya pertambangan dan laporan PDF deterministik.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}
