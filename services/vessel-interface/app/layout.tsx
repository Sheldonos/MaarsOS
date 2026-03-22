import type { Metadata } from 'next';
import './globals.css';
import TopNav from '@/components/layout/TopNav';
import Sidebar from '@/components/layout/Sidebar';
import Footer from '@/components/layout/Footer';
import WebSocketProvider from '@/components/providers/WebSocketProvider';

export const metadata: Metadata = {
  title: 'MAARS — Vision Layer',
  description: 'Master Autonomous Agentic Runtime System',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-bg text-text font-sans antialiased">
        <WebSocketProvider>
          <div className="flex flex-col h-screen">
            <TopNav />
            <div className="flex flex-1 overflow-hidden">
              <Sidebar />
              <main className="flex-1 overflow-auto bg-bg">
                {children}
              </main>
            </div>
            <Footer />
          </div>
        </WebSocketProvider>
      </body>
    </html>
  );
}

// Made with Bob
