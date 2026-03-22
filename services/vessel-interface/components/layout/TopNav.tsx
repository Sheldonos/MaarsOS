'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { clsx } from 'clsx';
import { useAgentStore, useInboxStore, useCostStore, useSimulationStore } from '@/store';
import StatusDot from '@/components/ui/StatusDot';

export default function TopNav() {
  const pathname = usePathname();
  
  // Get connection status from stores
  const agentConnected = useAgentStore((state) => state.isConnected);
  const inboxConnected = useInboxStore((state) => state.isConnected);
  const costConnected = useCostStore((state) => state.isConnected);
  const simulationConnected = useSimulationStore((state) => state.isConnected);
  
  // Determine overall connection status
  const allConnected = agentConnected && inboxConnected && costConnected && simulationConnected;
  const someConnected = agentConnected || inboxConnected || costConnected || simulationConnected;
  const connectionStatus = allConnected ? 'online' : someConnected ? 'warning' : 'offline';
  
  const links = [
    { href: '/canvas', label: 'Canvas' },
    { href: '/inbox', label: 'Inbox' },
    { href: '/simulation', label: 'Simulation' },
    { href: '/agents', label: 'Agents' },
    { href: '/settings/trust', label: 'Trust' },
    { href: '/telemetry', label: 'Telemetry' },
  ];
  
  return (
    <nav className="sticky top-0 z-50 h-12 bg-bg border-b border-border flex items-center px-6 gap-8">
      <Link href="/" className="text-[13px] font-semibold text-text-bright tracking-wide">
        MAARS<span className="text-primary">OS</span>
      </Link>
      
      <div className="flex gap-1 flex-1">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={clsx(
              'text-[13px] px-2.5 py-1 rounded-md transition-colors',
              pathname === link.href
                ? 'text-text-bright bg-surface2'
                : 'text-text-dim hover:text-text hover:bg-surface2'
            )}
          >
            {link.label}
          </Link>
        ))}
      </div>
      
      <div className="flex items-center gap-3 ml-auto">
        {/* WebSocket Connection Status */}
        <div className="flex items-center gap-2 text-[11px] bg-surface2 border border-border px-2 py-0.5 rounded-md">
          <StatusDot status={connectionStatus} />
          <span className="text-text-dim font-mono">
            {allConnected ? 'Connected' : someConnected ? 'Partial' : 'Disconnected'}
          </span>
        </div>
        
        <span className="text-[11px] text-text-dim bg-surface2 border border-border px-2 py-0.5 rounded-md font-mono">
          v1.0.0
        </span>
        <span className="text-[11px] text-green bg-surface2 border border-green/30 px-2 py-0.5 rounded-md font-mono">
          Week 2 Day 3 ✓
        </span>
      </div>
    </nav>
  );
}

// Made with Bob
