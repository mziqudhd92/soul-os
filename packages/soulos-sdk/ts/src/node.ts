import { readFile } from "fs/promises";
import { basename } from "path";
import { SoulOSClient, type RegisterAvatarResponse } from "./index";

/** Node-only helper: register from a `.soul` or `.soul.json` file path. */
export async function registerAvatarFromFile(
  client: SoulOSClient,
  soulPath: string
): Promise<RegisterAvatarResponse> {
  const lower = soulPath.toLowerCase();
  if (lower.endsWith(".soul") && !lower.endsWith(".soul.json")) {
    const bytes = await readFile(soulPath);
    return client.registerAvatarFromRaw(bytes, basename(soulPath));
  }

  const payload = JSON.parse(await readFile(soulPath, "utf8"));
  return client.registerAvatar(payload);
}
