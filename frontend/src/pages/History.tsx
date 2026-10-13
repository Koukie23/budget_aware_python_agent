import { Button, Card, Table, Typography } from "antd";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type TaskSummary } from "../api";
import { PREFERENCE_LABELS, StatusTag, usd } from "../labels";

export function History() {
  const [rows, setRows] = useState<TaskSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const load = () => {
    setLoading(true);
    api
      .tasks()
      .then((r) => {
        setRows(r);
        setError(null);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <Card className="panel" title="History" extra={<Button onClick={load}>Refresh</Button>}>
      {error && <Typography.Text type="danger">Could not load history: {error}</Typography.Text>}
      <Table<TaskSummary>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        locale={{ emptyText: "No runs yet." }}
        scroll={{ x: 960 }}
        onRow={(r) => ({ onClick: () => navigate(`/?task=${r.id}`), style: { cursor: "pointer" } })}
        columns={[
          { title: "Run", dataIndex: "id", width: 70, render: (v) => `#${v}` },
          { title: "Function", dataIndex: "function_name", render: (v) => <span className="mono">{v}</span> },
          { title: "Requirement", dataIndex: "requirement", ellipsis: true },
          { title: "Preference", dataIndex: "preference", width: 120, render: (v: TaskSummary["preference"]) => PREFERENCE_LABELS[v] },
          { title: "Status", dataIndex: "status", width: 160, render: (v: TaskSummary["status"]) => <StatusTag status={v} /> },
          { title: "Calls", dataIndex: "model_calls", width: 70 },
          { title: "Cost", dataIndex: "total_actual_cost_usd", width: 110, render: usd },
          { title: "Created", dataIndex: "created_at", width: 180, render: (v) => new Date(v).toLocaleString("en-US") },
        ]}
      />
    </Card>
  );
}
