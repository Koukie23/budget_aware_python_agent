import { useEffect, useState } from "react";
import { api, isActive, type TaskDetail } from "./api";

const POLL_MS = 1000;

export function useTaskPolling(taskId: number | null) {
  const [task, setTask] = useState<TaskDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (taskId == null) {
      setTask(null);
      return;
    }
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const tick = async () => {
      try {
        const t = await api.task(taskId);
        if (cancelled) return;
        setTask(t);
        setError(null);
        if (isActive(t.status)) timer = setTimeout(tick, POLL_MS);
      } catch (e) {
        if (cancelled) return;
        setError((e as Error).message);
        timer = setTimeout(tick, POLL_MS * 3);
      }
    };
    tick();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [taskId]);

  return { task, error };
}
