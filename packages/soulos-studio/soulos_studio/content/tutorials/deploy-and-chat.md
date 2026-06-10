# Deploy to kernel and test chat

Register your soul with the SoulOS kernel and stream a live conversation.

## Prerequisites

Start the kernel stack:

```bash
docker compose up soulos-kernel db ollama
# Kernel: http://localhost:8000
```

Studio should point at the kernel (default `SOULOS_KERNEL_URL=http://localhost:8000`).

## Step 1 — Build your soul

Use the **Wizard** or sliders until the JSON panel shows **valid**.

## Step 2 — Deploy

Click **Deploy to kernel**. On success you will see:

```
Avatar: Your Name (<uuid>)
```

Chat input unlocks when deploy succeeds.

## Step 3 — Send a message

Type in **Test chat** and press **Send**. The kernel streams System 1 text via SSE `event: message`.

## Step 4 — Watch MSV drift

During the stream, System 2 may emit `event: msv_update` with updated HEXACO values. Studio updates sliders and the radar chart when drift arrives.

## Troubleshooting

| Error | Fix |
|-------|-----|
| Kernel unreachable | Start `soulos-kernel` or set `SOULOS_KERNEL_URL` |
| Empty responses | Pull an Ollama model (`llama3`, `nomic-embed-text`) |
| 422 on deploy | Fix validation errors in the JSON panel |

## curl equivalent

```bash
curl -X POST http://localhost:8000/v1/avatars \
  -H "Content-Type: application/json" \
  -d @my-bot.soul.json

curl -N -X POST http://localhost:8000/chat/generate \
  -H "Content-Type: application/json" \
  -d '{"bot_id":"<id>","message":"Hello"}'
```

## Next

- **Tutorial** tab → **15-minute quickstart**
- **Docs** tab → **API reference** for the full SSE protocol
