import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, Button, Badge, StatusDot } from '@/components/ui';

export default function Home() {
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-bright mb-2">
          MAARS Vision Layer
        </h1>
        <p className="text-text-dim text-lg">
          Enterprise Operating System for AI Agents
        </p>
      </div>

      {/* Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-dim text-sm mb-1">System Status</p>
                <div className="flex items-center gap-2">
                  <StatusDot status="online" size="md" pulse />
                  <span className="text-text-bright font-semibold">Online</span>
                </div>
              </div>
              <Badge variant="success">Week 1 ✓</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div>
              <p className="text-text-dim text-sm mb-1">Active Agents</p>
              <p className="text-2xl font-bold text-text-bright font-mono">0 / 10,000</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div>
              <p className="text-text-dim text-sm mb-1">Services Online</p>
              <p className="text-2xl font-bold text-text-bright font-mono">8 / 13</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>
            Navigate to core MAARS features
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Link href="/canvas">
              <Button variant="secondary" className="w-full justify-start">
                🎨 Canvas
              </Button>
            </Link>
            <Link href="/inbox">
              <Button variant="secondary" className="w-full justify-start">
                📥 Inbox
              </Button>
            </Link>
            <Link href="/simulation">
              <Button variant="secondary" className="w-full justify-start">
                🔬 Simulation
              </Button>
            </Link>
            <Link href="/agents">
              <Button variant="secondary" className="w-full justify-start">
                🤖 Agents
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Implementation Progress */}
      <Card>
        <CardHeader>
          <CardTitle>Implementation Progress</CardTitle>
          <CardDescription>
            Week 1 Days 1-4 Complete
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-text">Phase 1: Foundation</span>
                <Badge variant="success">100%</Badge>
              </div>
              <div className="h-2 bg-surface2 rounded-full overflow-hidden">
                <div className="h-full bg-green" style={{ width: '100%' }} />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-text">Phase 2: Components</span>
                <Badge variant="success">100%</Badge>
              </div>
              <div className="h-2 bg-surface2 rounded-full overflow-hidden">
                <div className="h-full bg-green" style={{ width: '100%' }} />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-text">Phase 3: WebSocket Hub</span>
                <Badge variant="warning">Next</Badge>
              </div>
              <div className="h-2 bg-surface2 rounded-full overflow-hidden">
                <div className="h-full bg-yellow" style={{ width: '0%' }} />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Next Steps */}
      <Card className="mt-8">
        <CardHeader>
          <CardTitle>Next Steps</CardTitle>
          <CardDescription>
            Week 2: WebSocket Real-Time Layer
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-text-dim">
            <li className="flex items-start gap-2">
              <span className="text-yellow">→</span>
              <span>Implement WebSocket hub in vessel-gateway (Go)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-yellow">→</span>
              <span>Create 4 channel handlers (swarm, guardrails, costs, simulation)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-yellow">→</span>
              <span>Set up Zustand stores for real-time state management</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-yellow">→</span>
              <span>Test end-to-end WebSocket event flow</span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

// Made with Bob
