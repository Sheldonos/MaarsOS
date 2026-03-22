'use client';

export default function Footer() {
  return (
    <footer className="h-8 bg-surface border-t border-border flex items-center justify-between px-6 text-[11px] text-text-dim">
      <div className="flex items-center gap-4">
        <span>MAARS v1.0.0</span>
        <span>•</span>
        <span>13 Services Online</span>
        <span>•</span>
        <span className="text-green">Week 1 Complete</span>
      </div>
      
      <div className="flex items-center gap-4">
        <span>Latency: <span className="text-text font-mono">85ms</span></span>
        <span>•</span>
        <span>Uptime: <span className="text-text font-mono">99.97%</span></span>
        <span>•</span>
        <span>Cache Hit: <span className="text-text font-mono">72%</span></span>
      </div>
    </footer>
  );
}

// Made with Bob
