import { PlayCircleOutlined } from "@ant-design/icons";
import {
  Alert,
  App,
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Row,
  Segmented,
  Select,
  Space,
  Typography,
} from "antd";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, ApiError, isActive, type Example, type MockScenario, type Preference } from "../api";
import { RunResult } from "../components/RunResult";
import { PREFERENCE_HINTS, PREFERENCE_LABELS, SCENARIO_LABELS } from "../labels";
import { useTaskPolling } from "../useTaskPolling";

const { Text } = Typography;

interface FormValues {
  requirement: string;
  function_signature: string;
  tests: string;
  preference: Preference;
  budget_usd: number;
  mock_scenario: MockScenario;
}

const DEFAULTS: Partial<FormValues> = {
  preference: "balanced",
  budget_usd: 0.05,
  mock_scenario: "pass",
};

export function Workbench() {
  const [form] = Form.useForm<FormValues>();
  const { message } = App.useApp();
  const [examples, setExamples] = useState<Example[]>([]);
  const [exampleId, setExampleId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [params, setParams] = useSearchParams();
  const taskId = params.get("task") ? Number(params.get("task")) : null;
  const { task, error } = useTaskPolling(taskId);

  useEffect(() => {
    api.examples().then(setExamples).catch(() => message.error("Could not load examples."));
  }, []);

  const loadExample = (id: number | null) => {
    setExampleId(id);
    const ex = examples.find((e) => e.example_task_id === id);
    if (!ex) return;
    form.setFieldsValue({
      requirement: ex.requirement,
      function_signature: ex.function_signature,
      tests: ex.feedback_tests.join("\n"),
    });
  };

  const onFinish = async (values: FormValues) => {
    const tests = values.tests
      .split("\n")
      .map((t) => t.trim())
      .filter(Boolean);
    const ex = examples.find((e) => e.example_task_id === exampleId);
    setSubmitting(true);
    try {
      const { id } = await api.createTask({
        requirement: values.requirement.trim(),
        function_signature: values.function_signature.trim(),
        feedback_tests: tests,
        test_imports: ex?.test_imports ?? [],
        preference: values.preference,
        budget_usd: values.budget_usd,
        mock_scenario: values.mock_scenario,
        example_task_id: exampleId,
      });
      setParams({ task: String(id) });
    } catch (e) {
      const err = e as ApiError;
      message.error(err.details?.length ? err.details.join(" ") : err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const running = task != null && isActive(task.status);

  return (
    <Row gutter={[20, 20]}>
      <Col xs={24} lg={10}>
        <Card className="panel" title="Task">
          <Form
            form={form}
            layout="vertical"
            initialValues={DEFAULTS}
            onFinish={onFinish}
            onValuesChange={(changed) => {
              if ("requirement" in changed || "function_signature" in changed || "tests" in changed) {
                setExampleId(null);
              }
            }}
            requiredMark={false}
          >
            <Form.Item label="Load an MBPP example">
              <Select
                allowClear
                placeholder="Choose an example to fill the form"
                value={exampleId}
                onChange={(v) => loadExample(v ?? null)}
                options={examples.map((e) => ({
                  value: e.example_task_id,
                  label: `#${e.example_task_id} · ${e.function_name} (${e.split})`,
                }))}
              />
            </Form.Item>
            <Form.Item
              name="requirement"
              label="Requirement"
              rules={[{ required: true, min: 10, message: "Describe the function in at least 10 characters." }]}
            >
              <Input.TextArea rows={3} placeholder="Return the second largest distinct element in a list; return None if there are fewer than two." />
            </Form.Item>
            <Form.Item
              name="function_signature"
              label="Function signature"
              rules={[
                { required: true, message: "Enter the function signature." },
                { pattern: /^def\s+[A-Za-z_]\w*\s*\(.*\)\s*(->\s*.+)?:?$/, message: "Use the form: def name(arg1, arg2)" },
              ]}
            >
              <Input placeholder="def second_largest(nums)" className="mono" />
            </Form.Item>
            <Form.Item
              name="tests"
              label="Feedback tests"
              extra="One assert per line. These tests are visible to the agent and used for repair."
              rules={[
                { required: true, message: "Add at least one test." },
                {
                  validator: (_, v: string) => {
                    const bad = (v ?? "").split("\n").map((l) => l.trim()).filter(Boolean).filter((l) => !l.startsWith("assert "));
                    return bad.length ? Promise.reject(new Error("Every line must start with 'assert '.")) : Promise.resolve();
                  },
                },
              ]}
            >
              <Input.TextArea rows={5} className="mono" placeholder="assert second_largest([1, 3, 2]) == 2" />
            </Form.Item>
            <Form.Item
              name="preference"
              label="Preference"
              extra={<Form.Item noStyle shouldUpdate>{() => PREFERENCE_HINTS[form.getFieldValue("preference") as Preference]}</Form.Item>}
            >
              <Segmented
                block
                options={(Object.keys(PREFERENCE_LABELS) as Preference[]).map((p) => ({ value: p, label: PREFERENCE_LABELS[p] }))}
              />
            </Form.Item>
            <Form.Item
              name="budget_usd"
              label="Strong model budget (USD)"
              extra="Only strong-model API calls are charged. The fine-tuned model runs locally."
              rules={[{ required: true, message: "Enter a budget." }]}
            >
              <InputNumber min={0.000001} max={10} step={0.01} prefix="$" style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              name="mock_scenario"
              label="Mock model behavior"
              extra="Both models are mocked until the fine-tuned model is trained. Custom tasks without an MBPP example cannot be solved by the mock."
            >
              <Select options={(Object.keys(SCENARIO_LABELS) as MockScenario[]).map((s) => ({ value: s, label: SCENARIO_LABELS[s] }))} />
            </Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" icon={<PlayCircleOutlined />} loading={submitting} disabled={running}>
                {running ? "Running..." : "Run agent"}
              </Button>
              <Text type="secondary">Up to 3 model calls; strong-model calls must fit the budget.</Text>
            </Space>
          </Form>
        </Card>
      </Col>
      <Col xs={24} lg={14}>
        {error && <Alert type="error" showIcon message={`Could not load the run: ${error}`} style={{ marginBottom: 16 }} />}
        <RunResult task={task} />
      </Col>
    </Row>
  );
}
