import { Card, CardHeader, CardTitle, CardDescription, CardContent, Button, Badge } from '@/components/ui';

export default function SimulationPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-bright mb-2">
          Simulation & Dry-Run Engine
        </h1>
        <p className="text-text-dim text-lg">
          Agent-Based Modeling (ABM) for cost and success prediction
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardContent className="pt-6">
            <p className="text-text-dim text-sm mb-1">Simulations Run</p>
            <p className="text-2xl font-bold text-text-bright font-mono">0</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <p className="text-text-dim text-sm mb-1">Avg Confidence</p>
            <p className="text-2xl font-bold text-text-bright font-mono">--</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <p className="text-text-dim text-sm mb-1">Cost Saved</p>
            <p className="text-2xl font-bold text-green font-mono">$0.00</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <p className="text-text-dim text-sm mb-1">Prediction Accuracy</p>
            <p className="text-2xl font-bold text-text-bright font-mono">--</p>
          </CardContent>
        </Card>
      </div>

      {/* Simulation Form */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Run New Simulation</CardTitle>
          <CardDescription>
            Test a workflow before executing with real agents
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-text-dim mb-2">
                Goal Description
              </label>
              <textarea
                className="w-full bg-surface2 border border-border rounded-md p-3 text-text text-sm"
                rows={3}
                placeholder="Research 50 competitors and generate a market analysis report..."
                disabled
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm text-text-dim mb-2">
                  Simulation Runs
                </label>
                <input
                  type="number"
                  className="w-full bg-surface2 border border-border rounded-md p-2 text-text text-sm font-mono"
                  placeholder="1000"
                  disabled
                />
              </div>

              <div>
                <label className="block text-sm text-text-dim mb-2">
                  Time Horizon (hours)
                </label>
                <input
                  type="number"
                  className="w-full bg-surface2 border border-border rounded-md p-2 text-text text-sm font-mono"
                  placeholder="4"
                  disabled
                />
              </div>

              <div>
                <label className="block text-sm text-text-dim mb-2">
                  Max Budget
                </label>
                <input
                  type="number"
                  className="w-full bg-surface2 border border-border rounded-md p-2 text-text text-sm font-mono"
                  placeholder="10.00"
                  disabled
                />
              </div>
            </div>

            <Button variant="primary" disabled>
              Run Simulation
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Example Results */}
      <Card className="opacity-50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Example: Market Research Simulation</CardTitle>
              <CardDescription>
                1,000 Monte Carlo runs completed
              </CardDescription>
            </div>
            <Badge variant="success">87% Confidence</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Cost Prediction */}
            <div>
              <h4 className="text-sm font-semibold text-text-bright mb-3">
                Predicted Cost (USD)
              </h4>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-surface2 p-3 rounded-lg">
                  <p className="text-xs text-text-dim mb-1">P50 (Median)</p>
                  <p className="text-lg font-bold text-text font-mono">$2.40</p>
                </div>
                <div className="bg-surface2 p-3 rounded-lg">
                  <p className="text-xs text-text-dim mb-1">P90</p>
                  <p className="text-lg font-bold text-yellow font-mono">$4.10</p>
                </div>
                <div className="bg-surface2 p-3 rounded-lg">
                  <p className="text-xs text-text-dim mb-1">P99 (Worst Case)</p>
                  <p className="text-lg font-bold text-red font-mono">$7.80</p>
                </div>
              </div>
            </div>

            {/* Duration Prediction */}
            <div>
              <h4 className="text-sm font-semibold text-text-bright mb-3">
                Predicted Duration (minutes)
              </h4>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-surface2 p-3 rounded-lg">
                  <p className="text-xs text-text-dim mb-1">P50 (Median)</p>
                  <p className="text-lg font-bold text-text font-mono">18</p>
                </div>
                <div className="bg-surface2 p-3 rounded-lg">
                  <p className="text-xs text-text-dim mb-1">P90</p>
                  <p className="text-lg font-bold text-yellow font-mono">34</p>
                </div>
                <div className="bg-surface2 p-3 rounded-lg">
                  <p className="text-xs text-text-dim mb-1">P99 (Worst Case)</p>
                  <p className="text-lg font-bold text-red font-mono">62</p>
                </div>
              </div>
            </div>

            {/* Risk Factors */}
            <div>
              <h4 className="text-sm font-semibold text-text-bright mb-3">
                Risk Factors
              </h4>
              <div className="space-y-2">
                <div className="flex items-center justify-between bg-surface2 p-3 rounded-lg">
                  <div>
                    <p className="text-sm text-text">Web scraping rate limits</p>
                    <p className="text-xs text-text-dim">Probability: 23%</p>
                  </div>
                  <Badge variant="warning">LOW</Badge>
                </div>
                <div className="flex items-center justify-between bg-surface2 p-3 rounded-lg">
                  <div>
                    <p className="text-sm text-text">API quota exhaustion</p>
                    <p className="text-xs text-text-dim">Probability: 12%</p>
                  </div>
                  <Badge variant="info">MEDIUM</Badge>
                </div>
              </div>
            </div>

            {/* Recommendations */}
            <div className="bg-primary/10 border border-primary/30 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-primary mb-2">
                Recommended Configuration
              </h4>
              <ul className="text-sm text-text space-y-1">
                <li>• Liability Cap: <span className="font-mono">$8.00</span></li>
                <li>• Timeout: <span className="font-mono">45 minutes</span></li>
                <li>• Success Rate: <span className="font-mono">91%</span></li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Made with Bob
