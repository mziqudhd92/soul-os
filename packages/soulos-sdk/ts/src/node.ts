import { readFile } from "fs/promises";
import { SoulOSClient, type RegisterAvatarResponse } from "./index";

/** Node-only helper: register from a `.soul.json` file path. */
export async function registerAvatarFromFile(
  client: SoulOSClient,
  soulPath: string
): Promise<RegisterAvatarResponse> {
  const payload = JSON.parse(await readFile(soulPath, "utf8"));
  return client.registerAvatar(payload);
}
