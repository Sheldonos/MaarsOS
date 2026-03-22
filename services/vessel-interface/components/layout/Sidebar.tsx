'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { clsx } from 'clsx';
import { useState } from 'react';

interface SidebarProps {
  className?: string;
}

export default function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  
  const sections = [
    {
      title: 'Core',
      items: [
        { href: '/canvas', label: 'Canvas', icon: '🎨' },
        { href: '/inbox', label: 'Inbox', icon: '📥' },
        { href: '/agents', label: 'Agents', icon: '🤖' },
      ],
    },
    {
      title: 'Analysis',
      items: [
        { href: '/simulation', label: 'Simulation', icon: '🔬' },
        { href: '/telemetry', label: 'Telemetry', icon: '📊' },
        { href: '/economics', label: 'Economics', icon: '💰' },
      ],
    },
    {
      title: 'Settings',
      items: [
        { href: '/settings/trust', label: 'Trust', icon: '🔒' },
        { href: '/settings/integrations', label: 'Integrations', icon: '🔌' },
        { href: '/settings/personas', label: 'Personas', icon: '👥' },
      ],
    },
  ];
  
  return (
    <aside
      className={clsx(
        'h-full bg-surface border-r border-border transition-all duration-200',
        collapsed ? 'w-16' : 'w-56',
        className
      )}
    >
      <div className="flex flex-col h-full">
        {/* Collapse Toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="h-12 flex items-center justify-center border-b border-border hover:bg-surface2 transition-colors"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <span className="text-text-dim text-sm">
            {collapsed ? '→' : '←'}
          </span>
        </button>
        
        {/* Navigation Sections */}
        <nav className="flex-1 overflow-y-auto py-4">
          {sections.map((section) => (
            <div key={section.title} className="mb-6">
              {!collapsed && (
                <h3 className="px-4 mb-2 text-[11px] font-semibold text-text-dim uppercase tracking-wider">
                  {section.title}
                </h3>
              )}
              <div className="space-y-1 px-2">
                {section.items.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={clsx(
                      'flex items-center gap-3 px-2 py-2 rounded-md text-[13px] transition-colors',
                      pathname === item.href
                        ? 'bg-surface2 text-text-bright'
                        : 'text-text-dim hover:text-text hover:bg-surface2'
                    )}
                    title={collapsed ? item.label : undefined}
                  >
                    <span className="text-base">{item.icon}</span>
                    {!collapsed && <span>{item.label}</span>}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </nav>
        
        {/* Status Footer */}
        <div className="border-t border-border p-4">
          {!collapsed ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-text-dim">Status</span>
                <span className="text-green">● Online</span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-text-dim">Agents</span>
                <span className="text-text font-mono">0 / 10,000</span>
              </div>
            </div>
          ) : (
            <div className="flex justify-center">
              <span className="text-green text-lg">●</span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

// Made with Bob
