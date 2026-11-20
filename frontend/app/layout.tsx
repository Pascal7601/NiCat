import './globals.css';
import type { Metadata } from 'next';
export const metadata: Metadata = { title:'NiCat — Practice with purpose', description:'Independent university examination preparation, beginning with MMU BBIT.' };
export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="en"><body>{children}</body></html>; }
