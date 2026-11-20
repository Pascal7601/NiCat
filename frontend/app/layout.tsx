import "./globals.css";

import type { Metadata } from "next";

import NetworkStatus from "@/components/NetworkStatus";

export const metadata: Metadata = {
    title: "NiCat — Practice with purpose",
    description: "Independent university examination preparation.",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <body>
                <NetworkStatus />
                {children}
            </body>
        </html>
    );
}
