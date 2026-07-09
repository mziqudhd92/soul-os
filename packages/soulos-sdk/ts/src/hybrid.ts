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

export type HybridPrepareResponse = {
  bot_id: string;
  identity: Record<string, unknown>;
  memories: string[];
  system_prompt: string;
  inner_monologue: string;
};

export type HybridCompleteResponse = {
  status: string;
  ingested?: boolean;
  reflect?: string;
  bot_id?: string;
  current_msv?: Record<string, unknown>;
};

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
    } = {}
  ): Promise<HybridCompleteResponse | null> {
    if (!this.enabled) return null;
    const botId = options.botId ?? this.botId;
    if (!botId) return null;
    const reflect = options.reflect ?? Boolean(options.userMessage);
    try {
      const res = await fetch(`${this.baseUrl}/hybrid/complete`, {
        method: "POST",
        headers: this.headers(),
        body: JSON.stringify({
          bot_id: botId,
          summary,
          user_message: options.userMessage,
          session_id: options.sessionId,
          reflect,
          reflect_async: options.reflectAsync ?? true,
        }),
      });
      if (!res.ok) return null;
      return (await res.json()) as HybridCompleteResponse;
    } catch {
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
    const reply = await generate(prepared.system_prompt, prepared);
    const completed = await this.completeTurn(reply.slice(0, 2000), {
      userMessage: query,
      sessionId: options.sessionId,
      reflect: options.reflect ?? true,
    });
    return {
      reply,
      systemPrompt: prepared.system_prompt,
      prepare: prepared,
      complete: completed,
    };
  }
}
