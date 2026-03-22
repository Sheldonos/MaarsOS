-- MAARS AstraDB Schema
-- This schema replaces PostgreSQL, Neo4j, Qdrant, Redis, and ClickHouse
-- Based on MAARS Master Implementation Guide Section 2

-- Note: Keyspace creation is handled via AstraDB UI/API
-- CREATE KEYSPACE maars WITH replication = {'class': 'NetworkTopologyStrategy', 'datacenter1': 3};

USE maars;

-- ============================================================================
-- TENANT & IDENTITY LAYER
-- ============================================================================

CREATE TABLE IF NOT EXISTS tenants (
    tenant_id UUID PRIMARY KEY,
    name TEXT,
    plan_tier TEXT,
    credit_balance DECIMAL,
    settings_json TEXT,
    created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    tenant_id UUID,
    user_id UUID,
    email TEXT,
    role TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, user_id)
);

CREATE TABLE IF NOT EXISTS agent_identities (
    tenant_id UUID,
    agent_id UUID,
    identity_id UUID,
    token_hash TEXT,
    scope_json TEXT,
    delegation_chain_json TEXT,
    expires_at TIMESTAMP,
    PRIMARY KEY (tenant_id, agent_id, identity_id)
);

CREATE TABLE IF NOT EXISTS delegation_chains (
    tenant_id UUID,
    chain_id UUID,
    identity_id UUID,
    delegator_user_id UUID,
    purpose TEXT,
    liability_cap_usd DECIMAL,
    policy_ref TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, chain_id)
);

-- ============================================================================
-- ORCHESTRATION LAYER
-- ============================================================================

CREATE TABLE IF NOT EXISTS goal_packets (
    tenant_id UUID,
    goal_id UUID,
    owner_user_id UUID,
    description TEXT,
    priority TEXT,
    total_budget_usd DECIMAL,
    spent_usd DECIMAL,
    status TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    PRIMARY KEY (tenant_id, goal_id)
);

CREATE TABLE IF NOT EXISTS task_graphs (
    tenant_id UUID,
    goal_id UUID,
    graph_id UUID,
    tasks_json TEXT,
    dependencies_json TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, goal_id, graph_id)
);

CREATE TABLE IF NOT EXISTS task_definitions (
    tenant_id UUID,
    goal_id UUID,
    task_id UUID,
    assigned_agent_id UUID,
    instructions TEXT,
    tool_allowlist list<TEXT>,
    budget_ceiling_usd DECIMAL,
    model_tier TEXT,
    status TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    PRIMARY KEY ((tenant_id, goal_id), task_id)
);

CREATE TABLE IF NOT EXISTS agent_profiles (
    tenant_id UUID,
    agent_id UUID,
    name TEXT,
    capabilities list<TEXT>,
    status TEXT,
    model_id TEXT,
    model_tier TEXT,
    performance_score FLOAT,
    system_prompt TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, agent_id)
);

-- ============================================================================
-- MEMORY LAYER (Vector Store + Knowledge Graph)
-- ============================================================================

CREATE TABLE IF NOT EXISTS memory_nodes (
    tenant_id UUID,
    agent_id UUID,
    node_id UUID,
    content TEXT,
    embedding VECTOR<FLOAT, 1536>,
    memory_type TEXT,
    importance_score FLOAT,
    provenance_hash TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, agent_id, node_id)
);

-- Create Storage-Attached Index for vector search
CREATE CUSTOM INDEX IF NOT EXISTS memory_nodes_embedding_idx 
ON memory_nodes(embedding) USING 'StorageAttachedIndex'
WITH OPTIONS = {'similarity_function': 'cosine'};

CREATE TABLE IF NOT EXISTS kg_nodes (
    tenant_id UUID,
    kg_node_id UUID,
    entity_type TEXT,
    entity_name TEXT,
    properties_json TEXT,
    embedding VECTOR<FLOAT, 1536>,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, kg_node_id)
);

CREATE CUSTOM INDEX IF NOT EXISTS kg_nodes_embedding_idx 
ON kg_nodes(embedding) USING 'StorageAttachedIndex'
WITH OPTIONS = {'similarity_function': 'cosine'};

CREATE TABLE IF NOT EXISTS kg_edges (
    tenant_id UUID,
    source_kg_node_id UUID,
    relationship_type TEXT,
    target_kg_node_id UUID,
    weight FLOAT,
    properties_json TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY ((tenant_id, source_kg_node_id), relationship_type, target_kg_node_id)
);

-- ============================================================================
-- EXECUTION LAYER
-- ============================================================================

CREATE TABLE IF NOT EXISTS sandbox_configs (
    tenant_id UUID,
    sandbox_id UUID,
    task_id UUID,
    image TEXT,
    resource_limits_json TEXT,
    network_policy TEXT,
    status TEXT,
    created_at TIMESTAMP,
    terminated_at TIMESTAMP,
    PRIMARY KEY (tenant_id, sandbox_id)
);

CREATE TABLE IF NOT EXISTS tool_executions (
    tenant_id UUID,
    task_id UUID,
    exec_id UUID,
    sandbox_id UUID,
    tool_name TEXT,
    args_json TEXT,
    result_json TEXT,
    cost_usd DECIMAL,
    duration_ms INT,
    status TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY ((tenant_id, task_id), exec_id)
);

CREATE TABLE IF NOT EXISTS artifacts (
    tenant_id UUID,
    artifact_id UUID,
    task_id UUID,
    file_path TEXT,
    file_type TEXT,
    size_bytes BIGINT,
    checksum TEXT,
    s3_url TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, artifact_id)
);

-- ============================================================================
-- OBSERVABILITY LAYER
-- ============================================================================

CREATE TABLE IF NOT EXISTS trace_spans (
    tenant_id UUID,
    trace_id UUID,
    span_id UUID,
    parent_span_id UUID,
    agent_id UUID,
    task_id UUID,
    operation_name TEXT,
    duration_ms INT,
    status TEXT,
    attributes_json TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY ((tenant_id, trace_id), span_id)
);

CREATE TABLE IF NOT EXISTS guardrail_decisions (
    tenant_id UUID,
    decision_id UUID,
    span_id UUID,
    task_id UUID,
    agent_id UUID,
    confidence_score FLOAT,
    action TEXT,
    reason TEXT,
    reasoning_chain_json TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, decision_id)
);

CREATE TABLE IF NOT EXISTS context_graph_snapshots (
    tenant_id UUID,
    snapshot_id UUID,
    goal_id UUID,
    reasoning_chain_json TEXT,
    outcome TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, snapshot_id)
);

CREATE TABLE IF NOT EXISTS failure_patterns (
    tenant_id UUID,
    pattern_id UUID,
    pattern_type TEXT,
    frequency INT,
    affected_agent_types list<TEXT>,
    recommended_fix TEXT,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    PRIMARY KEY (tenant_id, pattern_id)
);

-- ============================================================================
-- VESSEL-OBSERVABILITY SERVICE TABLES
-- ============================================================================

-- Guardrail policies define rules and constraints for agent behavior
CREATE TABLE IF NOT EXISTS guardrail_policies (
    tenant_id UUID,
    policy_id UUID,
    name TEXT,
    type TEXT,  -- e.g., 'content_filter', 'cost_limit', 'rate_limit', 'security'
    config MAP<TEXT, TEXT>,  -- Policy-specific configuration as key-value pairs
    severity TEXT,  -- 'low', 'medium', 'high', 'critical'
    enabled BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (tenant_id, policy_id)
);

-- Policy violations track when agents violate guardrail policies
CREATE TABLE IF NOT EXISTS policy_violations (
    tenant_id UUID,
    violation_id UUID,
    policy_id UUID,
    agent_id UUID,
    task_id UUID,
    severity TEXT,
    details TEXT,  -- JSON string with violation details
    timestamp TIMESTAMP,
    PRIMARY KEY ((tenant_id, policy_id), timestamp, violation_id)
) WITH CLUSTERING ORDER BY (timestamp DESC, violation_id ASC);

-- Create index for querying violations by agent
CREATE INDEX IF NOT EXISTS policy_violations_agent_idx ON policy_violations (agent_id);

-- Create index for querying violations by task
CREATE INDEX IF NOT EXISTS policy_violations_task_idx ON policy_violations (task_id);

-- Anomaly detections track unusual patterns in agent behavior or system metrics
CREATE TABLE IF NOT EXISTS anomaly_detections (
    tenant_id UUID,
    anomaly_id UUID,
    agent_id UUID,
    metric_type TEXT,  -- e.g., 'response_time', 'token_usage', 'error_rate'
    value DOUBLE,
    threshold DOUBLE,
    severity TEXT,  -- 'low', 'medium', 'high'
    timestamp TIMESTAMP,
    PRIMARY KEY ((tenant_id, agent_id), timestamp, anomaly_id)
) WITH CLUSTERING ORDER BY (timestamp DESC, anomaly_id ASC);

-- Create index for querying anomalies by metric type
CREATE INDEX IF NOT EXISTS anomaly_detections_metric_idx ON anomaly_detections (metric_type);

-- Metrics history stores time-series metrics for all services
CREATE TABLE IF NOT EXISTS metrics_history (
    service TEXT,
    metric_name TEXT,
    metric_id UUID,
    value DOUBLE,
    labels MAP<TEXT, TEXT>,  -- Additional metric labels/dimensions
    timestamp TIMESTAMP,
    PRIMARY KEY ((service, metric_name), timestamp, metric_id)
) WITH CLUSTERING ORDER BY (timestamp DESC, metric_id ASC);

-- ============================================================================
-- ECONOMICS LAYER
-- ============================================================================

CREATE TABLE IF NOT EXISTS transactions (
    tenant_id UUID,
    tx_id UUID,
    task_id UUID,
    tx_type TEXT,
    amount_usd DECIMAL,
    on_chain_hash TEXT,
    status TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, tx_id)
);

CREATE TABLE IF NOT EXISTS escrow_actions (
    tenant_id UUID,
    escrow_id UUID,
    task_id UUID,
    agent_id UUID,
    action_payload_json TEXT,
    liability_cap_usd DECIMAL,
    status TEXT,
    rules_engine_decision_json TEXT,
    approved_by UUID,
    approved_at TIMESTAMP,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, escrow_id)
);

CREATE TABLE IF NOT EXISTS compliance_audits (
    tenant_id UUID,
    audit_id UUID,
    task_id UUID,
    escrow_id UUID,
    passed BOOLEAN,
    flags_json TEXT,
    policy_version TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, audit_id)
);

CREATE TABLE IF NOT EXISTS legal_contracts (
    tenant_id UUID,
    contract_id UUID,
    goal_id UUID,
    contract_type TEXT,
    parties_json TEXT,
    terms_hash TEXT,
    on_chain_address TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, contract_id)
);

-- ============================================================================
-- VESSEL-ECONOMICS SERVICE TABLES
-- ============================================================================

-- Escrow accounts track tenant balances and locked funds
CREATE TABLE IF NOT EXISTS escrow_accounts (
    tenant_id UUID PRIMARY KEY,
    balance DECIMAL,  -- Available balance in USD
    locked_balance DECIMAL,  -- Funds locked for pending transactions
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Escrow transactions record all financial movements
CREATE TABLE IF NOT EXISTS escrow_transactions (
    tenant_id UUID,
    transaction_id UUID,
    type TEXT,  -- 'deposit', 'withdrawal', 'lock', 'unlock', 'charge'
    amount DECIMAL,
    task_id UUID,  -- Optional: associated task
    status TEXT,  -- 'pending', 'completed', 'failed', 'cancelled'
    timestamp TIMESTAMP,
    PRIMARY KEY ((tenant_id), timestamp, transaction_id)
) WITH CLUSTERING ORDER BY (timestamp DESC, transaction_id ASC);

-- Create index for querying transactions by task
CREATE INDEX IF NOT EXISTS escrow_transactions_task_idx ON escrow_transactions (task_id);

-- Cost records track detailed usage costs per agent/task
CREATE TABLE IF NOT EXISTS cost_records (
    tenant_id UUID,
    cost_id UUID,
    agent_id UUID,
    task_id UUID,
    provider TEXT,  -- 'openai', 'anthropic', 'google', etc.
    model TEXT,  -- Model name
    input_tokens INT,
    output_tokens INT,
    cost DECIMAL,  -- Cost in USD
    timestamp TIMESTAMP,
    PRIMARY KEY ((tenant_id, agent_id), timestamp, cost_id)
) WITH CLUSTERING ORDER BY (timestamp DESC, cost_id ASC);

-- Create index for querying costs by task
CREATE INDEX IF NOT EXISTS cost_records_task_idx ON cost_records (task_id);

-- Create index for querying costs by provider
CREATE INDEX IF NOT EXISTS cost_records_provider_idx ON cost_records (provider);

-- Budget limits define spending constraints per tenant
CREATE TABLE IF NOT EXISTS budget_limits (
    tenant_id UUID PRIMARY KEY,
    limit_amount DECIMAL,  -- Maximum allowed spending
    used_amount DECIMAL,  -- Current spending in period
    period TEXT,  -- 'daily', 'weekly', 'monthly'
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Audit trail for compliance and regulatory requirements
CREATE TABLE IF NOT EXISTS audit_trail (
    tenant_id UUID,
    audit_id UUID,
    event_type TEXT,  -- 'transaction', 'budget_change', 'policy_update', etc.
    details TEXT,  -- JSON string with event details
    timestamp TIMESTAMP,
    PRIMARY KEY ((tenant_id), timestamp, audit_id)
) WITH CLUSTERING ORDER BY (timestamp DESC, audit_id ASC);

-- Create index for querying audit events by type
CREATE INDEX IF NOT EXISTS audit_trail_event_type_idx ON audit_trail (event_type);

-- Invoices for billing and financial reporting
CREATE TABLE IF NOT EXISTS invoices (
    tenant_id UUID,
    invoice_id UUID,
    period_start TIMESTAMP,
    period_end TIMESTAMP,
    total_amount DECIMAL,
    status TEXT,  -- 'draft', 'issued', 'paid', 'overdue', 'cancelled'
    generated_at TIMESTAMP,
    PRIMARY KEY (tenant_id, invoice_id)
);

-- Create index for querying invoices by status
CREATE INDEX IF NOT EXISTS invoices_status_idx ON invoices (status);

-- ============================================================================
-- INTEGRATION LAYER (MCP & Connectors)
-- ============================================================================

CREATE TABLE IF NOT EXISTS connector_definitions (
    connector_id UUID PRIMARY KEY,
    name TEXT,
    display_name TEXT,
    category TEXT,
    description TEXT,
    input_schema_json TEXT,
    output_schema_json TEXT,
    auth_type TEXT,
    required_scopes list<TEXT>,
    is_active BOOLEAN,
    created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tenant_connectors (
    tenant_id UUID,
    connector_id UUID,
    config_id UUID,
    vault_secret_path TEXT,
    is_enabled BOOLEAN,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, connector_id)
);

CREATE TABLE IF NOT EXISTS task_tool_allowlists (
    task_id UUID PRIMARY KEY,
    tenant_id UUID,
    allowed_tool_names list<TEXT>,
    created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    tenant_id UUID,
    webhook_id UUID,
    target_url TEXT,
    secret_hash TEXT,
    events list<TEXT>,
    is_active BOOLEAN,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, webhook_id)
);

-- ============================================================================
-- SIMULATION & RESEARCH LAYER
-- ============================================================================

CREATE TABLE IF NOT EXISTS simulation_runs (
    tenant_id UUID,
    sim_id UUID,
    goal_id UUID,
    world_state_json TEXT,
    strategy_json TEXT,
    confidence_score FLOAT,
    recommendation TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    PRIMARY KEY (tenant_id, sim_id)
);

CREATE TABLE IF NOT EXISTS simulation_results (
    tenant_id UUID,
    sim_id UUID,
    result_id UUID,
    predicted_outcome TEXT,
    confidence FLOAT,
    data_provenance_json TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY ((tenant_id, sim_id), result_id)
);

-- ============================================================================
-- SELF-IMPROVEMENT LAYER
-- ============================================================================

CREATE TABLE IF NOT EXISTS model_evaluations (
    tenant_id UUID,
    eval_id UUID,
    agent_id UUID,
    task_id UUID,
    success_score FLOAT,
    judge_model TEXT,
    rubric_json TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, eval_id)
);

CREATE TABLE IF NOT EXISTS optimization_runs (
    tenant_id UUID,
    run_id UUID,
    agent_id UUID,
    trigger_reason TEXT,
    baseline_score FLOAT,
    improved_score FLOAT,
    prompt_versions_tested INT,
    winner_prompt_version UUID,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, run_id)
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    tenant_id UUID,
    version_id UUID,
    agent_id UUID,
    prompt_text TEXT,
    performance_score FLOAT,
    is_active BOOLEAN,
    created_at TIMESTAMP,
    PRIMARY KEY (tenant_id, version_id)
);

-- ============================================================================
-- AGENT TEMPLATES (No-Code Builder)
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_templates (
    template_id UUID PRIMARY KEY,
    name TEXT,
    category TEXT,
    description TEXT,
    default_tier TEXT,
    default_tool_allowlist list<TEXT>,
    system_prompt_persona TEXT,
    example_goals list<TEXT>,
    visual_graph_json TEXT,
    compiled_task_graph_json TEXT,
    thumbnail_url TEXT,
    created_at TIMESTAMP
);