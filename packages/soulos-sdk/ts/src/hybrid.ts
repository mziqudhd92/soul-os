const DEFAULT_CLOUD_URL = "https://api.soulos.dev";

export type SoulHybridClientConfig = {
  baseUrl?: string;
  apiKey?: string;
  botId?: string;
  enabled?: boolean;
  gatewaySecret?: string;
  accountId?: string;
  timeoutMs?: number;
};

export type EnsureAvatarResponse = {
  id: string;
  name: string;
  role: string;
  baseline_msv: Record<string, unknown>;
  current_msv: Record<string, unknown>;
};

export type ContractContext = {
  contract_id?: string;
  expected_step: string;
  missing_slots: string[];
  filled_slots: Record<string, unknown>;
  reject_tokens: string[];
  ui_progress: { step_index: number; step_count: number; label: string };
  allowed_intents: string[];
  prompt_appendix: string;
  turn_version: number;
};

export type HybridPrepareResponse = {
  bot_id: string;
  identity: Record<string, unknown>;
  memories: string[];
  system_prompt: string;
  inner_monologue: string;
  contract_context?: ContractContext;
};

export type HybridCompleteResponse = {
  status: string;
  ingested?: boolean;
  reflect?: string;
  bot_id?: string;
  current_msv?: Record<string, unknown>;
  turn?: {
    step: string;
    slots: Record<string, unknown>;
    advanced: boolean;
    turn_version: number;
  };
};

export function mergeContractIntoSystemPrompt(
  prepareResponse: HybridPrepareResponse | Record<string, unknown>
): string {
  const base = String(prepareResponse.system_prompt ?? "");
  const ctx = prepareResponse.contract_context as ContractContext | undefined;
  const appendix = ctx?.prompt_appendix;
  if (!appendix) return base;
  if (!base) return appendix;
  return `${base.replace(/\s+$/, "")}\n\n${appendix}`;
}


export class SoulHybridClient {
  private readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly gatewaySecret?: string;
  private readonly accountId?: string;
  private readonly timeoutMs: number;
  public botId?: string;
  public enabled: boolean;

  constructor(config: SoulHybridClientConfig = {}) {
    if (config.baseUrl) {
      this.baseUrl = config.baseUrl.replace(/\/$/, "");
      this.apiKey = config.apiKey;
    } else if (config.apiKey) {
      this.baseUrl = DEFAULT_CLOUD_URL;
      this.apiKey = config.apiKey;
    } else {
      this.baseUrl = "http://localhost:8000";
    }
    this.botId = config.botId;
    this.gatewaySecret = config.gatewaySecret;
    this.accountId = config.accountId;
    this.timeoutMs = config.timeoutMs ?? 60000;
    this.enabled = config.enabled ?? true;
  }

  private headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.apiKey) h["Authorization"] = `Bearer ${this.apiKey}`;
    if (this.gatewaySecret) h["X-SoulOS-Gateway-Secret"] = this.gatewaySecret;
    if (this.accountId) h["X-SoulOS-Account-Id"] = this.accountId;
    return h;
  }

  async isReady(): Promise<boolean> {
    if (!this.enabled) return false;
    try {
      const res = await fetch(`${this.baseUrl}/ready`, { headers: this.headers() });
      if (!res.ok) return false;
      const data = await res.json();
      return data.status === "ok";
    } catch {
      return false;
    }
  }

  async ensureAvatar(
    externalKey: string,
    soul: Record<string, unknown>,
    runtimeConfig?: Record<string, unknown>
  ): Promise<EnsureAvatarResponse> {
    const res = await fetch(`${this.baseUrl}/v1/avatars/ensure`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({
        external_key: externalKey,
        soul,
        runtime_config: runtimeConfig,
      }),
    });
    const body = await res.json();
    if (!res.ok) {
      throw new Error(body.detail || `ensureAvatar failed (${res.status})`);
    }
    this.botId = body.id;
    return body as EnsureAvatarResponse;
  }

  async prepareTurn(
    query: string,
    options: {
      botId?: string;
      sessionId?: string;
      topK?: number;
    } = {}
  ): Promise<HybridPrepareResponse | null> {
    if (!this.enabled) return null;
    const botId = options.botId ?? this.botId;
    if (!botId) return null;
    try {
      const res = await fetch(`${this.baseUrl}/hybrid/prepare`, {
        method: "POST",
        headers: this.headers(),
        body: JSON.stringify({
          bot_id: botId,
          query,
          session_id: options.sessionId,
          top_k: options.topK ?? 5,
        }),
      });
      if (!res.ok) return null;
      return (await res.json()) as HybridPrepareResponse;
    } catch {
      return null;
    }
  }

  async completeTurn(
    summary: string,
    options: {
      userMessage?: string;
      botId?: string;
      sessionId?: string;
      reflect?: boolean;
      reflectAsync?: boolean;
      filledSlots?: Record<string, unknown> | null;
      intent?: string;
      assistantText?: string;
      expectedVersion?: number;
      idempotencyKey?: string;
      advance?: boolean;
      expectedStep?: string;
      raiseOnError?: boolean;
    } = {}
  ): Promise<HybridCompleteResponse | null> {
    if (!this.enabled) return null;
    const botId = options.botId ?? this.botId;
    if (!botId) return null;
    const reflect = options.reflect ?? Boolean(options.userMessage);
    const contractMode =
      options.filledSlots !== undefined ||
      options.expectedVersion !== undefined ||
      options.intent !== undefined ||
      options.idempotencyKey !== undefined;
    const idempotencyKey =
      options.idempotencyKey ?? (contractMode ? crypto.randomUUID() : undefined);
    const body: Record<string, unknown> = {
      bot_id: botId,
      summary,
      user_message: options.userMessage,
      session_id: options.sessionId,
      reflect,
      reflect_async: options.reflectAsync ?? true,
      advance: options.advance ?? true,
    };
    if (options.filledSlots !== undefined) body.filled_slots = options.filledSlots;
    if (options.intent !== undefined) body.intent = options.intent;
    if (options.assistantText !== undefined) body.assistant_text = options.assistantText;
    if (options.expectedVersion !== undefined) body.expected_version = options.expectedVersion;
    if (idempotencyKey !== undefined) body.idempotency_key = idempotencyKey;
    if (options.expectedStep !== undefined) body.expected_step = options.expectedStep;
    try {
      const res = await fetch(`${this.baseUrl}/hybrid/complete`, {
        method: "POST",
        headers: this.headers(),
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const problem = await res.json().catch(() => ({}));
        const code = String(problem.code || "");
        if (
          options.raiseOnError ||
          (contractMode && code.startsWith("TURN_"))
        ) {
          const err = new Error(problem.detail || `completeTurn failed (${res.status})`) as Error & {
            code?: string;
            status?: number;
            body?: Record<string, unknown>;
          };
          err.code = code || "UNKNOWN";
          err.status = res.status;
          err.body = problem;
          throw err;
        }
        return null;
      }
      return (await res.json()) as HybridCompleteResponse;
    } catch (e) {
      const code = (e as { code?: string }).code;
      if (
        options.raiseOnError ||
        (typeof code === "string" && code.startsWith("TURN_"))
      ) {
        throw e;
      }
      return null;
    }
  }

  async runTurn(
    query: string,
    generate: (systemPrompt: string, ctx: HybridPrepareResponse) => Promise<string>,
    options: {
      externalKey?: string;
      soul?: Record<string, unknown>;
      sessionId?: string;
      topK?: number;
      reflect?: boolean;
      mergeContract?: boolean;
      filledSlots?: Record<string, unknown> | null;
      intent?: string;
      advance?: boolean;
    } = {}
  ): Promise<{ reply: string; systemPrompt: string; prepare: HybridPrepareResponse; complete: HybridCompleteResponse | null }> {
    if (options.externalKey && options.soul) {
      await this.ensureAvatar(options.externalKey, options.soul);
    }
    const prepared = await this.prepareTurn(query, {
      sessionId: options.sessionId,
      topK: options.topK,
    });
    if (!prepared) {
      throw new Error("prepare_turn returned no context");
    }
    const mergeContract = options.mergeContract !== false;
    const systemPrompt = mergeContract
      ? mergeContractIntoSystemPrompt(prepared)
      : prepared.system_prompt;
    const reply = await generate(systemPrompt, prepared);
    const ctx = prepared.contract_context;
    const completed = await this.completeTurn(reply.slice(0, 2000), {
      userMessage: query,
      sessionId: options.sessionId,
      reflect: options.reflect ?? true,
      assistantText: reply,
      advance: options.advance ?? true,
      raiseOnError: true,
      ...(ctx?.turn_version !== undefined
        ? {
            expectedVersion: ctx.turn_version,
            expectedStep: ctx.expected_step,
          }
        : {}),
      ...(options.filledSlots !== undefined ? { filledSlots: options.filledSlots } : {}),
      ...(options.intent !== undefined ? { intent: options.intent } : {}),
    });
    return {
      reply,
      systemPrompt,
      prepare: prepared,
      complete: completed,
    };
  }
}
