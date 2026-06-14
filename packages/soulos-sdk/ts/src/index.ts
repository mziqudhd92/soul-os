export const DEFAULT_CLOUD_URL = "https://api.soulos.dev";

export {
  SoulHybridClient,
  type SoulHybridClientConfig,
  type EnsureAvatarResponse,
  type HybridPrepareResponse,
  type HybridCompleteResponse,
} from "./hybrid";

export type SoulOSClientConfig = {
  baseUrl?: string;
  apiKey?: string;
};

export type MsvUpdateEvent = {
  type: "msv_update";
  msv: Record<string, unknown>;
};

export type CognitiveStateEvent = {
  type: "cognitive_state";
  state: Record<string, unknown>;
};

export type MessageEvent = {
  type: "message";
  text: string;
};

export type ErrorEvent = {
  type: "error";
  message: string;
};

export type SoulStreamEvent =
  | MsvUpdateEvent
  | CognitiveStateEvent
  | MessageEvent
  | ErrorEvent;

export type RegisterAvatarResponse = {
  id: string;
  name: string;
  role: string;
  attachment_style?: string;
  baseline_msv: Record<string, unknown>;
  current_msv: Record<string, unknown>;
};

export type MemorySyncResponse = {
  status: string;
  imported: number;
  skipped: number;
  total: number;
};

export class SoulOSClient {
  private readonly baseUrl: string;
  private readonly apiKey?: string;

  constructor(config: SoulOSClientConfig = {}) {
    if (config.baseUrl) {
      this.baseUrl = config.baseUrl.replace(/\/$/, "");
      this.apiKey = config.apiKey;
    } else if (config.apiKey) {
      this.baseUrl = DEFAULT_CLOUD_URL;
      this.apiKey = config.apiKey;
    } else {
      this.baseUrl = "http://localhost:8000";
    }
  }

  private headers(contentType = "application/json"): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": contentType };
    if (this.apiKey) h["Authorization"] = `Bearer ${this.apiKey}`;
    return h;
  }

  async registerAvatar(soul: Record<string, unknown>): Promise<RegisterAvatarResponse> {
    const res = await fetch(`${this.baseUrl}/v1/avatars`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(soul),
    });

    const body = await res.json();
    if (!res.ok) {
      throw new Error(body.detail || `registerAvatar failed (${res.status})`);
    }
    return body as RegisterAvatarResponse;
  }

  async registerAvatarFromRaw(
    body: Uint8Array,
    filename: string,
    contentType = "text/markdown"
  ): Promise<RegisterAvatarResponse> {
    const headers = this.headers(contentType);
    headers["X-Filename"] = filename;
    const res = await fetch(`${this.baseUrl}/v1/avatars`, {
      method: "POST",
      headers,
      body: body as unknown as BodyInit,
    });
    const parsed = await res.json();
    if (!res.ok) {
      throw new Error(parsed.detail || `registerAvatarFromRaw failed (${res.status})`);
    }
    return parsed as RegisterAvatarResponse;
  }

  async ingestMemory(avatarId: string, content: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/memory/ingest`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ bot_id: avatarId, content }),
    });
    if (!res.ok) throw new Error(`ingestMemory failed (${res.status})`);
  }

  async syncMemory(
    avatarId: string,
    workspacePath: string
  ): Promise<MemorySyncResponse> {
    const res = await fetch(`${this.baseUrl}/memory/sync`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({
        bot_id: avatarId,
        workspace_path: workspacePath,
      }),
    });
    const body = await res.json();
    if (!res.ok) {
      throw new Error(body.detail || `syncMemory failed (${res.status})`);
    }
    return body as MemorySyncResponse;
  }

  async getIdentity(avatarId: string): Promise<Record<string, unknown>> {
    const res = await fetch(`${this.baseUrl}/bot/${avatarId}/identity`, {
      headers: this.headers(),
    });
    if (!res.ok) throw new Error(`getIdentity failed (${res.status})`);
    return res.json();
  }

  async updateState(avatarId: string, newMsv: Record<string, unknown>): Promise<void> {
    const res = await fetch(`${this.baseUrl}/state/update`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ bot_id: avatarId, new_msv: newMsv }),
    });
    if (!res.ok) throw new Error(`updateState failed (${res.status})`);
  }

  async *sendMessage(avatarId: string, message: string): AsyncGenerator<SoulStreamEvent> {
    const res = await fetch(`${this.baseUrl}/chat/generate`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ bot_id: avatarId, message }),
    });

    if (!res.ok || !res.body) {
      yield { type: "error", message: `sendMessage failed (${res.status})` };
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() || "";

      for (const block of blocks) {
        const eventMatch = block.match(/event: (.*)\n/);
        const dataMatch = block.match(/data: (.*)/);
        if (!eventMatch || !dataMatch) continue;

        const event = eventMatch[1].trim();
        const data = JSON.parse(dataMatch[1]);

        if (event === "message" && data.text) {
          yield { type: "message", text: data.text };
        } else if (event === "msv_update") {
          yield { type: "msv_update", msv: data };
        } else if (event === "cognitive_state") {
          yield { type: "cognitive_state", state: data };
        } else if (event === "error") {
          yield { type: "error", message: String(data) };
        }
      }
    }
  }
}
