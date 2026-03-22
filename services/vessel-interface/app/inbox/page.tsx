import { Card, CardHeader, CardTitle, CardDescription, CardContent, Button, Badge, StatusDot } from '@/components/ui';

export default function InboxPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-bright mb-2">
          Escrow Inbox
        </h1>
        <p className="text-text-dim text-lg">
          Human-in-the-loop approval for high-stakes agent actions
        </p>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-dim text-sm mb-1">Pending</p>
                <p className="text-2xl font-bold text-yellow font-mono">0</p>
              </div>
              <StatusDot status="pending" size="lg" pulse />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-dim text-sm mb-1">Approved</p>
                <p className="text-2xl font-bold text-green font-mono">0</p>
              </div>
              <StatusDot status="online" size="lg" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-dim text-sm mb-1">Rejected</p>
                <p className="text-2xl font-bold text-red font-mono">0</p>
              </div>
              <StatusDot status="error" size="lg" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-dim text-sm mb-1">Expired</p>
                <p className="text-2xl font-bold text-text-dim font-mono">0</p>
              </div>
              <StatusDot status="offline" size="lg" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Empty State */}
      <Card>
        <CardHeader>
          <CardTitle>No Pending Actions</CardTitle>
          <CardDescription>
            Agent actions requiring approval will appear here
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="border-2 border-dashed border-border rounded-lg p-12 text-center">
            <p className="text-text-dim mb-4">📥 Inbox is empty</p>
            <p className="text-sm text-text-dim mb-6">
              When agents attempt high-stakes actions (transactions, external API calls, etc.),
              they will be paused and routed here for your approval.
            </p>
            
            <div className="max-w-2xl mx-auto">
              <div className="bg-surface2 p-4 rounded-lg text-left">
                <p className="text-xs text-text-dim mb-2">Example Triggers:</p>
                <ul className="text-sm text-text space-y-1">
                  <li>• Transaction exceeds liability cap ($500)</li>
                  <li>• Agent attempts to send external email</li>
                  <li>• PII detected in output</li>
                  <li>• Execution failure after 3 retries</li>
                  <li>• Budget threshold exceeded (80%, 90%, 100%)</li>
                </ul>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Example Card (Hidden by default) */}
      <Card className="mt-8 opacity-50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Example: Budget Exceeded</CardTitle>
              <CardDescription>
                Task cost exceeds liability cap
              </CardDescription>
            </div>
            <Badge variant="warning">PENDING</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-text-dim mb-1">Goal ID</p>
                <p className="text-text font-mono">goal-abc123</p>
              </div>
              <div>
                <p className="text-text-dim mb-1">Task ID</p>
                <p className="text-text font-mono">task-xyz789</p>
              </div>
              <div>
                <p className="text-text-dim mb-1">Agent</p>
                <p className="text-text font-mono">agent-mid-001</p>
              </div>
              <div>
                <p className="text-text-dim mb-1">Estimated Cost</p>
                <p className="text-text font-mono">$0.75</p>
              </div>
            </div>

            <div className="bg-surface2 p-4 rounded-lg">
              <p className="text-sm text-text-dim mb-2">Proposed Action:</p>
              <p className="text-sm text-text">
                Execute web scraping task across 50 competitor websites
              </p>
            </div>

            <div className="flex gap-3">
              <Button variant="primary" disabled>Approve</Button>
              <Button variant="danger" disabled>Reject</Button>
              <Button variant="secondary" disabled>Defer</Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Made with Bob
