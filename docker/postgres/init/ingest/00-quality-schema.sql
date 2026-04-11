-- Quality audit schema for data validation results.
CREATE SCHEMA IF NOT EXISTS quality;

CREATE TABLE IF NOT EXISTS quality.audit_rules (
    rule_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    dataset TEXT NOT NULL,
    check_type TEXT NOT NULL,
    column_name TEXT,
    threshold JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS quality.audit_results (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rule_id TEXT REFERENCES quality.audit_rules(rule_id),
    run_id TEXT NOT NULL,
    status TEXT NOT NULL,
    measured_value JSONB,
    detail TEXT,
    checked_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_results_rule
    ON quality.audit_results(rule_id, checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_results_run
    ON quality.audit_results(run_id);
