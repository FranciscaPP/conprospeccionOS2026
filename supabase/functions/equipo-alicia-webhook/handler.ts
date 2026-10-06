export type QueueRow = {
  update_id: number;
  chat_id: number;
  text: string;
};

export type HandlerDependencies = {
  webhookSecret: string;
  allowedChatId: string;
  queue: (row: QueueRow) => Promise<"inserted" | "duplicate">;
  dispatch: (updateId: number) => Promise<void>;
  rollback: (updateId: number) => Promise<void>;
};


function secureEqual(left: string, right: string): boolean {
  const encoder = new TextEncoder();
  const a = encoder.encode(left);
  const b = encoder.encode(right);
  let difference = a.length ^ b.length;
  const length = Math.max(a.length, b.length);
  for (let index = 0; index < length; index += 1) {
    difference |= (a[index] ?? 0) ^ (b[index] ?? 0);
  }
  return difference === 0;
}


function json(status: number, body: Record<string, unknown>): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}


export async function handleTelegramUpdate(
  request: Request,
  dependencies: HandlerDependencies,
): Promise<Response> {
  if (request.method !== "POST") {
    return json(405, { ok: false, error: "method_not_allowed" });
  }
  const suppliedSecret = request.headers.get("x-telegram-bot-api-secret-token") ?? "";
  if (!secureEqual(suppliedSecret, dependencies.webhookSecret)) {
    return json(401, { ok: false, error: "unauthorized" });
  }

  let update: Record<string, unknown>;
  try {
    update = await request.json() as Record<string, unknown>;
  } catch {
    return json(200, { ok: true, ignored: "invalid_json" });
  }
  const updateId = Number(update.update_id);
  const message = update.message as Record<string, unknown> | undefined;
  const chat = message?.chat as Record<string, unknown> | undefined;
  const text = typeof message?.text === "string" ? message.text.trim() : "";
  const chatId = Number(chat?.id);
  if (!Number.isSafeInteger(updateId) || String(chatId) !== dependencies.allowedChatId || !text) {
    return json(200, { ok: true, ignored: "unsupported_update" });
  }

  try {
    const queued = await dependencies.queue({ update_id: updateId, chat_id: chatId, text });
    if (queued === "duplicate") {
      return json(200, { ok: true, duplicate: true });
    }
    try {
      await dependencies.dispatch(updateId);
    } catch (error) {
      await dependencies.rollback(updateId);
      throw error;
    }
    return json(200, { ok: true, queued: true });
  } catch {
    return json(500, { ok: false, error: "queue_or_dispatch_failed" });
  }
}
