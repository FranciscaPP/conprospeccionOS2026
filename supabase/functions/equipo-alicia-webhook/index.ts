import { createClient } from "jsr:@supabase/supabase-js@2";
import { handleTelegramUpdate, type QueueRow } from "./handler.ts";


const required = (name: string): string => {
  const value = Deno.env.get(name)?.trim();
  if (!value) throw new Error(`Missing required secret: ${name}`);
  return value;
};

const webhookSecret = required("TELEGRAM_WEBHOOK_SECRET");
const allowedChatId = required("TELEGRAM_SDR_CHAT_ID");
const repository = required("GITHUB_REPOSITORY");
const workflowToken = required("GITHUB_WORKFLOW_TOKEN");
const supabase = createClient(
  required("SUPABASE_URL"),
  required("SUPABASE_SERVICE_ROLE_KEY"),
  { auth: { persistSession: false, autoRefreshToken: false } },
);


async function queue(row: QueueRow): Promise<"inserted" | "duplicate"> {
  const { error } = await supabase.from("sdr_bot_queries").insert(row);
  if (!error) return "inserted";
  if (error.code === "23505") return "duplicate";
  throw new Error("Could not queue Telegram update");
}


async function rollback(updateId: number): Promise<void> {
  const { error } = await supabase
    .from("sdr_bot_queries")
    .delete()
    .eq("update_id", updateId)
    .eq("status", "queued");
  if (error) throw new Error("Could not roll back queued update");
}


async function dispatch(updateId: number): Promise<void> {
  const response = await fetch(
    `https://api.github.com/repos/${repository}/actions/workflows/equipo-alicia-cloud.yml/dispatches`,
    {
      method: "POST",
      headers: {
        accept: "application/vnd.github+json",
        authorization: `Bearer ${workflowToken}`,
        "content-type": "application/json",
        "x-github-api-version": "2022-11-28",
      },
      body: JSON.stringify({ ref: "main", inputs: { update_id: String(updateId) } }),
    },
  );
  if (!response.ok) throw new Error(`GitHub dispatch failed (${response.status})`);
}


Deno.serve((request) => handleTelegramUpdate(request, {
  webhookSecret,
  allowedChatId,
  queue,
  dispatch,
  rollback,
}));
