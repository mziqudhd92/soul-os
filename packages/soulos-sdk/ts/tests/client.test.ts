import { afterEach, describe, expect, it, vi } from "vitest";
import { DEFAULT_CLOUD_URL, SoulOSClient } from "../src/index";

describe("SoulOSClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("defaults to localhost when no config", () => {
    const client = new SoulOSClient();
    expect((client as unknown as { baseUrl: string }).baseUrl).toBe(
      "http://localhost:8000"
    );
  });

  it("uses cloud URL when only apiKey is set", () => {
    const client = new SoulOSClient({ apiKey: "sk_test" });
    expect((client as unknown as { baseUrl: string }).baseUrl).toBe(
      DEFAULT_CLOUD_URL
    );
  });

  it("registerAvatar posts soul JSON and returns body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: "bot-1",
        name: "Support",
        role: "Agent",
        baseline_msv: {},
        current_msv: {},
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const client = new SoulOSClient({ baseUrl: "http://k.test/" });
    const out = await client.registerAvatar({ name: "Support" });
    expect(out.id).toBe("bot-1");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://k.test/v1/avatars");
    expect(init.headers.Authorization).toBeUndefined();
    expect(JSON.parse(init.body)).toEqual({ name: "Support" });
  });

  it("sends Authorization bearer when apiKey set", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = new SoulOSClient({
      baseUrl: "http://k.test",
      apiKey: "sk_demo",
    });
    await client.ingestMemory("bot-1", "fact");
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe(
      "Bearer sk_demo"
    );
  });

  it("registerAvatar throws on error body.detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        json: async () => ({ detail: "SOUL_INVALID" }),
      })
    );
    const client = new SoulOSClient({ baseUrl: "http://k.test" });
    await expect(client.registerAvatar({})).rejects.toThrow(/SOUL_INVALID/);
  });

  it("sendMessage parses SSE message, msv_update, and cognitive_state", async () => {
    const sse = [
      'event: message\ndata: {"text":"Hello"}\n\n',
      'event: msv_update\ndata: {"hexaco":{"H":0.9}}\n\n',
      'event: cognitive_state\ndata: {"current_path":"s1"}\n\n',
    ].join("");
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(sse));
        controller.close();
      },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, body: stream, status: 200 })
    );

    const client = new SoulOSClient({ baseUrl: "http://k.test" });
    const events = [];
    for await (const e of client.sendMessage("bot-1", "hi")) {
      events.push(e);
    }
    expect(events).toEqual([
      { type: "message", text: "Hello" },
      { type: "msv_update", msv: { hexaco: { H: 0.9 } } },
      { type: "cognitive_state", state: { current_path: "s1" } },
    ]);
  });

  it("sendMessage yields error event when response not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 502, body: null })
    );
    const client = new SoulOSClient({ baseUrl: "http://k.test" });
    const events = [];
    for await (const e of client.sendMessage("bot-1", "hi")) {
      events.push(e);
    }
    expect(events[0]).toMatchObject({ type: "error" });
  });
});
