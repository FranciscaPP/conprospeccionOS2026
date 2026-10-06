import { handleTelegramUpdate, type HandlerDependencies } from "./handler.ts";


function assertEquals(actual: unknown, expected: unknown): void {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(`Expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
  }
}


function request(update: unknown, secret = "webhook-secret", method = "POST"): Request {
  return new Request("https://example.supabase.co/functions/v1/equipo-alicia-webhook", {
    method,
    headers: {
      "content-type": "application/json",
      "x-telegram-bot-api-secret-token": secret,
    },
    body: method === "POST" ? JSON.stringify(update) : undefined,
  });
}


function dependencies(queueResult: "inserted" | "duplicate" = "inserted") {
  const queued: Array<Record<string, unknown>> = [];
  const dispatched: number[] = [];
  const rolledBack: number[] = [];
  const deps: HandlerDependencies = {
    webhookSecret: "webhook-secret",
    allowedChatId: "123",
    queue: async (row) => {
      queued.push(row);
      return queueResult;
    },
    dispatch: async (updateId) => {
      dispatched.push(updateId);
    },
    rollback: async (updateId) => {
      rolledBack.push(updateId);
    },
  };
  return { deps, queued, dispatched, rolledBack };
}


Deno.test("rejects wrong method and wrong webhook secret", async () => {
  const first = dependencies();
  const wrongMethod = await handleTelegramUpdate(request({}, "webhook-secret", "GET"), first.deps);
  assertEquals(wrongMethod.status, 405);

  const second = dependencies();
  const wrongSecret = await handleTelegramUpdate(request({}, "wrong"), second.deps);
  assertEquals(wrongSecret.status, 401);
  assertEquals(second.queued, []);
});


Deno.test("ignores unauthorized chats and non-text updates without retry", async () => {
  const unauthorized = dependencies();
  const response = await handleTelegramUpdate(
    request({ update_id: 10, message: { chat: { id: 999 }, text: "resumen" } }),
    unauthorized.deps,
  );
  assertEquals(response.status, 200);
  assertEquals(unauthorized.queued, []);

  const nonText = dependencies();
  const nonTextResponse = await handleTelegramUpdate(
    request({ update_id: 11, message: { chat: { id: 123 }, photo: [{}] } }),
    nonText.deps,
  );
  assertEquals(nonTextResponse.status, 200);
  assertEquals(nonText.queued, []);
});


Deno.test("queues one authorized update and dispatches only its numeric id", async () => {
  const state = dependencies();
  const response = await handleTelegramUpdate(
    request({ update_id: 12345, message: { chat: { id: 123 }, text: "tareas de Balia" } }),
    state.deps,
  );

  assertEquals(response.status, 200);
  assertEquals(state.queued, [{ update_id: 12345, chat_id: 123, text: "tareas de Balia" }]);
  assertEquals(state.dispatched, [12345]);
});


Deno.test("duplicate update is acknowledged without another dispatch", async () => {
  const state = dependencies("duplicate");
  const response = await handleTelegramUpdate(
    request({ update_id: 12345, message: { chat: { id: 123 }, text: "resumen" } }),
    state.deps,
  );

  assertEquals(response.status, 200);
  assertEquals(state.dispatched, []);
});
