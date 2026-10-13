-- Budget-aware Python coding agent. All identifiers and system values are English.

CREATE TABLE IF NOT EXISTS tasks (
    id                       SERIAL PRIMARY KEY,
    example_task_id          INTEGER,
    requirement              TEXT        NOT NULL,
    function_name            TEXT        NOT NULL,
    function_signature       TEXT        NOT NULL,
    feedback_tests           JSONB       NOT NULL,
    test_imports             JSONB       NOT NULL DEFAULT '[]'::jsonb,
    preference               TEXT        NOT NULL CHECK (preference IN ('cheap', 'balanced', 'quality')),
    budget_usd               NUMERIC(12, 6) NOT NULL CHECK (budget_usd > 0),
    mock_scenario            TEXT        NOT NULL DEFAULT 'pass',
    executor                 TEXT,
    status                   TEXT        NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending', 'running', 'succeeded', 'failed',
                                               'budget_exhausted', 'system_error')),
    stop_reason              TEXT,
    policy                   TEXT,
    final_code               TEXT,
    model_calls              INTEGER     NOT NULL DEFAULT 0,
    total_estimated_cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 0,
    total_actual_cost_usd    NUMERIC(12, 6) NOT NULL DEFAULT 0,
    total_input_tokens       INTEGER     NOT NULL DEFAULT 0,
    total_output_tokens      INTEGER     NOT NULL DEFAULT 0,
    wall_time_sec            NUMERIC(10, 3),
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tasks_created_at_idx ON tasks (created_at DESC);

CREATE TABLE IF NOT EXISTS model_calls (
    id                 SERIAL PRIMARY KEY,
    task_id            INTEGER     NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
    step_index         INTEGER     NOT NULL,
    action             TEXT        NOT NULL CHECK (action IN ('generate', 'repair', 'escalate')),
    model_id           TEXT        NOT NULL,
    estimated_cost_usd NUMERIC(12, 6) NOT NULL,
    actual_cost_usd    NUMERIC(12, 6) NOT NULL,
    input_tokens       INTEGER     NOT NULL,
    output_tokens      INTEGER     NOT NULL,
    latency_sec        NUMERIC(10, 3) NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (task_id, step_index)
);

CREATE TABLE IF NOT EXISTS code_versions (
    id            SERIAL PRIMARY KEY,
    task_id       INTEGER NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
    model_call_id INTEGER NOT NULL REFERENCES model_calls (id) ON DELETE CASCADE,
    version       INTEGER NOT NULL,
    code          TEXT    NOT NULL,
    UNIQUE (task_id, version)
);

CREATE TABLE IF NOT EXISTS test_runs (
    id              SERIAL PRIMARY KEY,
    task_id         INTEGER NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
    code_version_id INTEGER NOT NULL REFERENCES code_versions (id) ON DELETE CASCADE,
    status          TEXT    NOT NULL CHECK (status IN ('passed', 'failed', 'timeout', 'system_error')),
    tests_passed    INTEGER NOT NULL,
    tests_total     INTEGER NOT NULL,
    duration_sec    NUMERIC(10, 3) NOT NULL,
    error_summary   TEXT
);
