import { Card, CardHeader, CardTitle, CardDescription, CardContent, Button, Badge, StatusDot } from '@/components/ui';

export default function AgentsPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-bright mb-2">
          Agent Swarm Management
        </h1>
        <p className="text-text-dim text-lg">
          Monitor and manage 10,000+ concurrent AI agents
        </p>
      </div>

      {/* Swarm Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-dim text-sm mb-1">Active Agents</p>
                <p className="text-2xl font-bold text-green font-mono">0</p>
              </div>
              <StatusDot status="online" size="lg" pulse />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div>
              <p className="text-text-dim text-sm mb-1">Idle Agents</p>
              <p className="text-2xl font-bold text-yellow font-mono">0</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div>
              <p className="text-text-dim text-sm mb-1">Failed Agents</p>
              <p className="text-2xl font-bold text-red font-mono">0</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div>
              <p className="text-text-dim text-sm mb-1">Total Capacity</p>
              <p className="text-2xl font-bold text-text-bright font-mono">10,000</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Agent Tiers */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Agent Cognitive Tiers</CardTitle>
          <CardDescription>
            Right-sizing engine distributes tasks across model tiers
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Nano Tier */}
            <div className="bg-surface2 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold text-text-bright">Nano Tier</h4>
                <Badge variant="success">Active: 0</Badge>
              </div>
              <p className="text-xs text-text-dim mb-3">
                Llama 3 8B, Mistral 7B - Simple formatting, data transformation
              </p>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-text-dim">Cost per 1M tokens</span>
                  <span className="text-text font-mono">$0.10</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-dim">Avg latency</span>
                  <span className="text-text font-mono">~200ms</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-dim">Network access</span>
                  <span className="text-text">None</span>
                </div>
              </div>
            </div>

            {/* Mid Tier */}
            <div className="bg-surface2 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold text-text-bright">Mid Tier</h4>
                <Badge variant="success">Active: 0</Badge>
              </div>
              <p className="text-xs text-text-dim mb-3">
                GPT-4o-mini, Claude Haiku - Research, analysis, code generation
              </p>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-text-dim">Cost per 1M tokens</span>
                  <span className="text-text font-mono">$1.50</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-dim">Avg latency</span>
                  <span className="text-text font-mono">~800ms</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-dim">Network access</span>
                  <span className="text-text">Whitelisted</span>
                </div>
              </div>
            </div>

            {/* Frontier Tier */}
            <div className="bg-surface2 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold text-text-bright">Frontier Tier</h4>
                <Badge variant="success">Active: 0</Badge>
              </div>
              <p className="text-xs text-text-dim mb-3">
                GPT-5.2, Claude Opus 4.6 - Complex reasoning, strategic planning
              </p>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-text-dim">Cost per 1M tokens</span>
                  <span className="text-text font-mono">$15.00</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-dim">Avg latency</span>
                  <span className="text-text font-mono">~2000ms</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-dim">Network access</span>
                  <span className="text-text">Full (monitored)</span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Agent Registry */}
      <Card className="mb-8">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Agent Registry</CardTitle>
              <CardDescription>
                All registered agents in the swarm
              </CardDescription>
            </div>
            <Button variant="primary" disabled>
              Spawn New Agent
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="border-2 border-dashed border-border rounded-lg p-12 text-center">
            <p className="text-text-dim mb-4">No agents registered</p>
            <p className="text-sm text-text-dim">
              Agents will appear here when goals are submitted and the orchestrator spawns them
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Example Agent Card */}
      <Card className="opacity-50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>agent-mid-001</CardTitle>
              <CardDescription>
                Mid-tier research agent
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <StatusDot status="online" size="md" pulse />
              <Badge variant="success">EXECUTING</Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-text-dim mb-1">Model</p>
                <p className="text-text font-mono">gpt-4o-mini</p>
              </div>
              <div>
                <p className="text-text-dim mb-1">Tier</p>
                <p className="text-text">Mid</p>
              </div>
              <div>
                <p className="text-text-dim mb-1">Tasks Completed</p>
                <p className="text-text font-mono">0</p>
              </div>
              <div>
                <p className="text-text-dim mb-1">Total Cost</p>
                <p className="text-text font-mono">$0.00</p>
              </div>
            </div>

            <div className="bg-surface2 p-3 rounded-lg">
              <p className="text-xs text-text-dim mb-2">Current Task:</p>
              <p className="text-sm text-text">
                Research competitor pricing strategies for SaaS products
              </p>
            </div>

            <div className="flex gap-2">
              <Button variant="secondary" size="sm" disabled>
                View Logs
              </Button>
              <Button variant="secondary" size="sm" disabled>
                Pause
              </Button>
              <Button variant="danger" size="sm" disabled>
                Terminate
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Made with Bob
