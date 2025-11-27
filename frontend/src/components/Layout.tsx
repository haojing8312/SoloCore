/**
 * Main layout component with navigation
 */

import { ReactNode } from 'react';
import { Navbar } from './Navbar';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <main className="flex-grow pt-24 pb-12 px-4 md:px-8 lg:px-0 max-w-5xl mx-auto w-full">
        {children}
      </main>
    </div>
  );
}
