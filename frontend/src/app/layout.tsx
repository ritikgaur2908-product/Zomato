import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TasteFinder - AI Restaurant Recommendations",
  description: "Personalized picks from real Zomato data — filtered by you, ranked by AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-surface text-onSurface min-h-screen pb-[80px] md:pb-0 font-bodyLg">
        {children}
      </body>
    </html>
  );
}
