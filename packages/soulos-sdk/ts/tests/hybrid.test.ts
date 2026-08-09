import { afterEach, describe, expect, it, vi } from "vitest";
import { mergeContractIntoSystemPrompt, SoulHybridClient } from "../src/hybrid";

describe("SoulHybridClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("prepareTurn posts hybrid prepare body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        bot_id: "bot-1",
        system_prompt: "You are Support.",
        memories: [],
        identity: {},
        inner_monologue: "Ready.",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const client = new SoulHybridClient({
      baseUrl: "http://kernel.test",
      botId: "bot-1",
      enabled: true,
    });
    const out = await client.prepareTurn("refund?");
    expect(out?.system_prompt).toContain("Support");
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://kernel.test/hybrid/prepare");
    expect(JSON.parse(init.body)).toMatchObject({
      bot_id: "bot-1",
      query: "refund?",
    });
  });

  it("prepareTurn returns null when disabled", async () => {
    const client = new SoulHybridClient({
      baseUrl: "http://kernel.test",
      botId: "bot-1",
      enabled: false,
    });
    expect(await client.prepareTurn("hi")).toBeNull();
  });

  it("completeTurn posts hybrid complete body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "success", ingested: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const client = new SoulHybridClient({
      baseUrl: "http://kernel.test",
      botId: "bot-1",
    });
    const out = await client.completeTurn("summary", {
      userMessage: "q",
      sessionId: "sess-1",
      reflect: false,
    });
    expect(out?.status).toBe("success");
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body).toMatchObject({
      bot_id: "bot-1",
      summary: "summary",
      user_message: "q",
      session_id: "sess-1",
      reflect: false,
    });
  });

  it("mergeContractIntoSystemPrompt appends appendix", () => {
    const merged = mergeContractIntoSystemPrompt({
      bot_id: "b",
      identity: {},
      memories: [],
      inner_monologue: "",
      system_prompt: "You are a concierge.",
      contract_context: {
        expected_step: "collect_dates",
        missing_slots: [],
        filled_slots: {},
        reject_tokens: [],
        ui_progress: { step_index: 0, step_count: 1, label: "collect_dates" },
        allowed_intents: [],
        prompt_appendix: "[SYSTEM DIRECTIVE: Step collect_dates.]",
        turn_version: 0,
      },
    });
    expect(merged).toContain("You are a concierge.");
    expect(merged).toContain("[SYSTEM DIRECTIVE");
  });

  it("completeTurn auto-generates idempotencyKey in contract mode", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "success",
        turn: { step: "confirm", turn_version: 1 },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = new SoulHybridClient({
      baseUrl: "http://kernel.test",
      botId: "bot-1",
    });
    await client.completeTurn("summary", {
      sessionId: "s1",
      reflect: false,
      filledSlots: { check_in: "2026-09-01" },
      expectedVersion: 0,
    });
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.idempotency_key).toBeTruthy();
    expect(body.expected_version).toBe(0);
  });
});
