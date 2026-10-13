import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  StopOutlined,
} from "@ant-design/icons";
import { Tag } from "antd";
import type { ReactNode } from "react";
import type { MockScenario, Preference, Step, TaskStatus } from "./api";
import { colors } from "./theme";

const STATUS: Record<TaskStatus, { label: string; color: string; icon: ReactNode }> = {
  pending: { label: "Pending", color: colors.secondary, icon: <ClockCircleOutlined /> },
  running: { label: "Running", color: colors.secondary, icon: <LoadingOutlined /> },
  succeeded: { label: "Passed", color: colors.primary, icon: <CheckCircleOutlined /> },
  failed: { label: "Failed", color: colors.danger, icon: <CloseCircleOutlined /> },
  budget_exhausted: { label: "Budget exhausted", color: colors.warning, icon: <StopOutlined /> },
  system_error: { label: "System error", color: colors.danger, icon: <ExclamationCircleOutlined /> },
};

export function StatusTag({ status }: { status: TaskStatus }) {
  const s = STATUS[status];
  return (
    <Tag icon={s.icon} color={s.color} style={{ marginInlineEnd: 0 }}>
      {s.label}
    </Tag>
  );
}

const TEST_STATUS: Record<Step["test_status"], { label: string; color: string }> = {
  passed: { label: "Passed", color: colors.primary },
  failed: { label: "Failed", color: colors.danger },
  timeout: { label: "Timeout", color: colors.warning },
  system_error: { label: "System error", color: colors.danger },
};

export function TestStatusTag({ status }: { status: Step["test_status"] }) {
  const s = TEST_STATUS[status];
  return <Tag color={s.color}>{s.label}</Tag>;
}

export const PREFERENCE_LABELS: Record<Preference, string> = {
  cheap: "Save cost",
  balanced: "Balanced",
  quality: "Quality first",
};

export const ACTION_LABELS: Record<Step["action"], string> = {
  generate: "Generate",
  repair: "Repair",
  escalate: "Escalate",
};

export const PREFERENCE_HINTS: Record<Preference, string> = {
  cheap: "Fine-tuned model generates and repairs. Never calls the strong model.",
  balanced: "Fine-tuned model generates and repairs, then the strong model if the budget allows.",
  quality: "Fine-tuned model generates, then goes straight to the strong model if tests fail.",
};

export const SCENARIO_LABELS: Record<MockScenario, string> = {
  pass: "Fine-tuned model passes on first try",
  repair: "Fine-tuned model fails once, then repairs",
  escalate: "Fine-tuned model keeps failing, strong model solves",
  exhaust: "All attempts fail",
  timeout: "First attempt loops forever (timeout)",
};

export const usd = (value: number | null | undefined) =>
  value == null ? "-" : `$${Number(value).toFixed(6)}`;
