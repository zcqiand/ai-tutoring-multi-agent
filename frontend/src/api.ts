// 请求层：同源相对 /api（dev 由 vite 代理，prod 由 nginx 承接，代码不写绝对地址）
import type {
  Health,
  SessionDetail,
  SessionSummary,
  SseEvent,
} from "./types";

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (body && body.detail !== undefined) detail = String(body.detail);
    } catch {
      /* 非 JSON 错误体，保留状态行 */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export function getHealth(): Promise<Health> {
  return fetch("/api/health").then((r) => asJson<Health>(r));
}

export function listSessions(): Promise<SessionSummary[]> {
  return fetch("/api/sessions").then((r) => asJson<SessionSummary[]>(r));
}

export function getSession(id: string): Promise<SessionDetail> {
  return fetch(`/api/sessions/${encodeURIComponent(id)}`).then((r) =>
    asJson<SessionDetail>(r)
  );
}

export function createSession(
  question: string
): Promise<{ id: string; question: string; created_at: string }> {
  return fetch("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  }).then((r) => asJson<{ id: string; question: string; created_at: string }>(r));
}

// run SSE：POST 流式响应，data 行内 JSON，空行分帧（与后端 _sse 约定一致）
export async function runSession(
  sid: string,
  maxSteps: number,
  onEvent: (ev: SseEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`/api/sessions/${encodeURIComponent(sid)}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ max_steps: maxSteps }),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`SSE 连接失败：${res.status} ${res.statusText}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const frame = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      for (const line of frame.split("\n")) {
        if (!line.startsWith("data: ")) continue;
        onEvent(JSON.parse(line.slice(6)) as SseEvent);
      }
    }
  }
}
