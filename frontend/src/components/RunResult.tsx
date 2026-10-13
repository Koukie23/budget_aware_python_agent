import { Alert, Card, Collapse, Descriptions, Empty, Segmented, Space, Statistic, Typography } from "antd";
import { useEffect, useState } from "react";
import { isActive, type TaskDetail } from "../api";
import { ACTION_LABELS, StatusTag, TestStatusTag, usd } from "../labels";
import { CodeBlock } from "./CodeBlock";

const { Text } = Typography;

export function RunResult({ task }: { task: TaskDetail | null }) {
  const [version, setVersion] = useState<number | null>(null);

  useEffect(() => {
    if (task?.steps.length) setVersion(task.steps[task.steps.length - 1].version);
    else setVersion(null);
  }, [task?.id, task?.steps.length]);

  if (!task) {
    return (
      <Card className="panel">
        <Empty description="No run yet. Fill in the task on the left and click Run agent." />
      </Card>
    );
  }

  const active = isActive(task.status);
  const shown = task.steps.find((s) => s.version === version) ?? task.steps[task.steps.length - 1];

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card
        className="panel"
        title={
          <Space>
            <span>Run #{task.id}</span>
            <StatusTag status={task.status} />
          </Space>
        }
      >
        {task.status === "budget_exhausted" && (
          <Alert type="warning" showIcon message="Budget exhausted" description={task.stop_reason} style={{ marginBottom: 16 }} />
        )}
        {(task.status === "failed" || task.status === "system_error") && (
          <Alert type="error" showIcon message={task.status === "failed" ? "Tests still failing" : "System error"} description={task.stop_reason} style={{ marginBottom: 16 }} />
        )}
        {active && (
          <Alert type="info" showIcon message="The agent is working. This page refreshes automatically." style={{ marginBottom: 16 }} />
        )}
        <div className="metrics">
          <Statistic title="Model calls" value={task.model_calls} suffix="/ 3" />
          <Statistic title="Strong model cost" value={usd(task.total_actual_cost_usd)} />
          <Statistic title="Estimated cost" value={usd(task.total_estimated_cost_usd)} />
          <Statistic title="Strong model budget" value={usd(task.budget_usd)} />
          <Statistic title="Tokens (in / out)" value={`${task.total_input_tokens} / ${task.total_output_tokens}`} />
          <Statistic title="Wall time" value={task.wall_time_sec == null ? "-" : `${Number(task.wall_time_sec).toFixed(2)} s`} />
        </div>
        <Descriptions size="small" column={1} style={{ marginTop: 16 }}>
          <Descriptions.Item label="Policy">{task.policy ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="Stop reason">{task.stop_reason ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="Executor">{task.executor ?? "-"}</Descriptions.Item>
        </Descriptions>
        <Text type="secondary" style={{ fontSize: 12 }}>
          Passing the visible tests does not guarantee the code is correct for every input.
        </Text>
      </Card>

      <Card className="panel" title="Execution timeline">
        {task.steps.length === 0 ? (
          <Empty description={active ? "Waiting for the first model call..." : "No model calls were made."} />
        ) : (
          <Collapse
            items={task.steps.map((s) => ({
              key: s.step_index,
              label: (
                <Space wrap>
                  <Text strong>
                    Step {s.step_index}: {ACTION_LABELS[s.action]}
                  </Text>
                  <Text type="secondary">{s.model_id}</Text>
                  <TestStatusTag status={s.test_status} />
                  <Text type="secondary">
                    Tests {s.tests_passed}/{s.tests_total} · {usd(s.actual_cost_usd)}
                  </Text>
                </Space>
              ),
              children: (
                <Space direction="vertical" style={{ width: "100%" }}>
                  <Descriptions size="small" column={{ xs: 1, sm: 1, md: 2 }}>
                    <Descriptions.Item label="Estimated cost">{usd(s.estimated_cost_usd)}</Descriptions.Item>
                    <Descriptions.Item label="Actual cost">{usd(s.actual_cost_usd)}</Descriptions.Item>
                    <Descriptions.Item label="Tokens (in / out)">
                      {s.input_tokens} / {s.output_tokens}
                    </Descriptions.Item>
                    <Descriptions.Item label="Test time">{Number(s.duration_sec).toFixed(2)} s</Descriptions.Item>
                  </Descriptions>
                  {s.error_summary && <CodeBlock code={s.error_summary} tone="error" />}
                </Space>
              ),
            }))}
          />
        )}
      </Card>

      <Card
        className="panel"
        title="Code"
        extra={
          task.steps.length > 1 && (
            <Segmented
              value={shown?.version}
              onChange={(v) => setVersion(Number(v))}
              options={task.steps.map((s) => ({ label: `v${s.version}`, value: s.version }))}
            />
          )
        }
      >
        {shown ? (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Space>
              <Text type="secondary">
                Version {shown.version} · {ACTION_LABELS[shown.action]} by {shown.model_id}
              </Text>
              <TestStatusTag status={shown.test_status} />
            </Space>
            <CodeBlock code={shown.code} />
          </Space>
        ) : (
          <Empty description="No code generated yet." />
        )}
      </Card>
    </Space>
  );
}
