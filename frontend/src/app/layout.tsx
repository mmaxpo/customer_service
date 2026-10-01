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
        <html lang="en" className={inter.variable} suppressHydrationWarning>
            <head>
                {/* Apply the saved theme before the first paint (see ThemeSwitch). */}
                <script dangerouslySetInnerHTML={{ __html: `try{if(localStorage.getItem("tajeran-theme")==="dark")document.documentElement.dataset.theme="dark"}catch(e){}` }} />
            </head>
            <body>{children}</body>
            </html>
    );
}
