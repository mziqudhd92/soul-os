/** Phase B / Phase A multi-agent handoff helpers. */

export function roleExternalKey(orgId: string, role: string): string {
  const org = (orgId || "").trim();
  const roleSlug = (role || "").trim().toLowerCase().replace(/\s+/g, "-");
  if (!org || !roleSlug) throw new Error("orgId and role are required");
  if (org.includes(":") || roleSlug.includes(":")) {
    throw new Error("orgId and role must not contain ':'");
  }
  return `org:${org}:${roleSlug}`;
}

export function conversationSessionId(conversationId: string): string {
  const cid = (conversationId || "").trim();
  if (!cid) throw new Error("conversationId is required");
  if (cid.startsWith("conv:")) return cid;
  return `conv:${cid}`;
}

export type HandoffParams = {
  fromBotId: string;
  toBotId: string;
  fromRole: string;
  toRole: string;
  conversationId: string;
  reason: string;
  summary: string;
  userMessage?: string;
  payload?: Record<string, unknown>;
  idempotencyKey?: string;
};

type RequestFn = (
  method: string,
  path: string,
  body?: Record<string, unknown>
) => Promise<{ ok: boolean; status: number; json: () => Promise<any> }>;

/** Prefer POST /v1/handoffs; caller supplies a thin request helper. */
export async function handoffTo(
  request: RequestFn,
  params: HandoffParams
): Promise<Record<string, unknown>> {
  if (params.fromBotId === params.toBotId) {
    throw new Error("fromBotId and toBotId must differ");
  }
  const sessionId = conversationSessionId(params.conversationId);
  const res = await request("POST", "/v1/handoffs", {
    from_bot_id: params.fromBotId,
    to_bot_id: params.toBotId,
    from_role: params.fromRole,
    to_role: params.toRole,
    conversation_id: params.conversationId,
    reason: params.reason,
    summary: params.summary,
    user_message: params.userMessage,
    payload: params.payload || {},
    idempotency_key: params.idempotencyKey,
  });
  if (!res.ok) {
    throw new Error(`handoff failed (${res.status})`);
  }
  const data = await res.json();
  return { ...data, session_id: data.session_id || sessionId };
}
