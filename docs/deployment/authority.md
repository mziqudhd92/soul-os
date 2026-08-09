# Flow authority (deploy ownership)

Coding agents and humans should know **which surface owns a hybrid flow** before changing deploy targets.

## Convention

Place `deploy/authority.json` at the app or pack root (example: [deploy/authority.json](../../deploy/authority.json)).

| Field | Meaning |
|-------|---------|
| `authority` | Human label for the source of truth (e.g. `"self-hosted kernel"`, `"Cloud Run API"`) |
| `canonical_deploy` | Path or URL to the real deploy entrypoint |
| `forbidden_surfaces` | Surfaces that must not be treated as the API authority |
| `notes` | Short guidance for agents |

## Example

```json
{
  "authority": "self-hosted SoulOS kernel",
  "canonical_deploy": "docker compose up --build",
  "forbidden_surfaces": [
    "vercel-only frontend deploy",
    "static GitHub Pages as API host"
  ],
  "notes": "Hybrid prepare/complete run on the kernel (:8000) or via the gateway (:8080). Do not treat the marketing site as the API."
}
```

Schema fragment: [spec/authority.schema.json](../../spec/authority.schema.json).
