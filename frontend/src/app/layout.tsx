import "./globals.css";
import "@xyflow/react/dist/style.css";
import { Inter } from "next/font/google";

const inter = Inter({
    subsets: ["latin"],
    variable: "--font-inter",
});

export const metadata = {
    title: "Tajeran.ai",
    description: "Support automation dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en" className={inter.variable}>
            <body>{children}</body>
            </html>
    );
}
