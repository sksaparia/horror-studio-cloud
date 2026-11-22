
const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json" }
  });

async function tg(env, method, body) {
  const r = await fetch(
    `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body)
    }
  );

  if (!r.ok) {
    throw new Error(`Telegram ${method}: ${r.status} ${await r.text()}`);
  }

  return r.json();
}

async function dispatchWorkflow(env, workflow, inputs = {}) {
  const url =
    `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${workflow}/dispatches`;

  const r = await fetch(url, {
    method: "POST",
    headers: {
      "authorization": `Bearer ${env.GITHUB_TOKEN}`,
      "accept": "application/vnd.github+json",
      "x-github-api-version": "2022-11-28",
      "content-type": "application/json"
    },
    body: JSON.stringify({
      ref: env.GITHUB_REF || "main",
      inputs
    })
  });

  if (!r.ok) {
    throw new Error(`GitHub dispatch failed: ${r.status} ${await r.text()}`);
  }
}

function getSceneNumber(message, nextScene) {
  const caption = (message.caption || "").trim();

  if (!caption) return nextScene;

  const match = caption.match(/^(?:scene[_\s-]*)?(\d{1,2})$/i);

  if (!match) {
    throw new Error("Caption must be a scene number, e.g. 1 or scene_01.");
  }

  return Number(match[1]);
}

async function handleVideo(message, env) {
  const chat = message.chat.id;
  const activeRaw = await env.HORROR_TOPICS.get("ACTIVE_JOB");

  if (!activeRaw) {
    await tg(env, "sendMessage", {
      chat_id: chat,
      text: "No active video job. Approve a topic first."
    });
    return;
  }

  const active = JSON.parse(activeRaw);
  const limit = active.format === "long" ? 48 : 5;

  const video = message.video ||
    (message.document &&
      message.document.mime_type === "video/mp4"
      ? message.document
      : null);

  if (!video) {
    await tg(env, "sendMessage", {
      chat_id: chat,
      text: "Please upload an MP4 video clip."
    });
    return;
  }

  const nextScene = Number(active.next_scene || 1);
  const scene = getSceneNumber(message, nextScene);

  if (scene < 1 || scene > limit) {
    await tg(env, "sendMessage", {
      chat_id: chat,
      text: `This ${active.format} project accepts scenes 1 to ${limit}.`
    });
    return;
  }

  if (video.file_size && video.file_size > 20 * 1024 * 1024) {
    await tg(env, "sendMessage", {
      chat_id: chat,
      text: "This clip exceeds the current Telegram Bot API download limit of 20 MB."
    });
    return;
  }

  await dispatchWorkflow(env, "production.yml", {
    action: "receive_clip",
    job_id: active.job_id,
    telegram_file_id: video.file_id,
    scene_number: String(scene),
    format: active.format
  });

  active.next_scene = Math.max(nextScene, scene + 1);
  active.uploaded_count = Number(active.uploaded_count || 0) + 1;

  if (active.next_scene > limit) {
    await env.HORROR_TOPICS.delete("ACTIVE_JOB");
  } else {
    await env.HORROR_TOPICS.put("ACTIVE_JOB", JSON.stringify(active));
  }

  await tg(env, "sendMessage", {
    chat_id: chat,
    text:
      `Clip received for processing.\n\n` +
      `Job: ${active.job_id}\n` +
      `Format: ${active.format.toUpperCase()}\n` +
      `Scene: ${scene}/${limit}\n\n` +
      `GitHub Actions will download and save this clip.`
  });
}

export default {
  async fetch(request, env) {
    const u = new URL(request.url);

    if (u.pathname.startsWith("/telegram/")) {
      if (u.pathname !== `/telegram/${env.TELEGRAM_WEBHOOK_SECRET}`) {
        return new Response("Not found", { status: 404 });
      }

      if (request.method !== "POST") {
        return new Response("OK");
      }

      const update = await request.json();

      if (update.message) {
        const m = update.message;
        const chat = m.chat.id;
        const text = (m.text || "").trim();

        if (
          !env.ALLOWED_TELEGRAM_CHAT_ID ||
          String(chat) !== String(env.ALLOWED_TELEGRAM_CHAT_ID)
        ) {
          return new Response("OK");
        }

        if (m.video || m.document) {
          await handleVideo(m, env);
          return new Response("OK");
        }

        if (text === "/start" || text === "/help") {
          await tg(env, "sendMessage", {
            chat_id: chat,
            text:
              "Horror Studio Cloud\n\n" +
              "/trending - Find horror topics\n" +
              "/format short - 5 clips\n" +
              "/format long - 48 clips\n" +
              "/repair JOB_ID | TOPIC_TITLE - Repair story manifest\n" +
              "/status - Check GitHub Actions\n\n" +
              "Approve a topic first. Then upload MP4 clips one by one.\n" +
              "Use caption 1, 2, 3... to identify scenes. Without a caption, the next scene number is assigned automatically."
          });
        } else if (text === "/trending") {
          await dispatchWorkflow(env, "topic-scout.yml");

          await tg(env, "sendMessage", {
            chat_id: chat,
            text: "Topic scouting started. I will send approval cards here."
          });
        } else if (text === "/status") {
          await tg(env, "sendMessage", {
            chat_id: chat,
            text: `Check cloud jobs:\nhttps://github.com/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions`
          });
        } else if (text === "/format short" || text === "/format long") {
          const format = text.endsWith("long") ? "long" : "short";

          await env.HORROR_TOPICS.put("SELECTED_FORMAT", format);

          await tg(env, "sendMessage", {
            chat_id: chat,
            text: `Selected format: ${format.toUpperCase()}. This will apply to the next approved topic.`
          });

        } else if (text.startsWith("/repair ")) {
          const input = text.slice(8).trim();
          const separator = input.indexOf("|");

          if (separator === -1) {
            await tg(env, "sendMessage", {
              chat_id: chat,
              text: "Use:\n/repair JOB_ID | TOPIC_TITLE"
            });
          } else {
            const id = input.slice(0, separator).trim();
            const title = input.slice(separator + 1).trim();

            if (
              !/^[A-Za-z0-9_-]{1,100}$/.test(id) ||
              !title ||
              title.length > 200
            ) {
              await tg(env, "sendMessage", {
                chat_id: chat,
                text: "Invalid Job ID or topic title."
              });
            } else {
              const activeRaw = await env.HORROR_TOPICS.get("ACTIVE_JOB");
              const active = activeRaw ? JSON.parse(activeRaw) : null;

              const format =
                active && active.job_id === id
                  ? active.format
                  : "short";

              await dispatchWorkflow(env, "production.yml", {
                action: "story_pack",
                job_id: id,
                topic_title: title,
                format
              });

              await tg(env, "sendMessage", {
                chat_id: chat,
                text:
                  "Manifest repair workflow started.\n\n" +
                  `Job ID: ${id}\n` +
                  `Format: ${format.toUpperCase()}\n` +
                  `Topic: ${title}\n\n` +
                  "The story pack will be regenerated in the existing job folder. Existing clips will not be deleted."
              });
            }
          }

        } else if (text.startsWith("/approve ")) {
          const id = text.split(/\s+/)[1];

          if (!/^[A-Za-z0-9_-]{1,100}$/.test(id || "")) {
            await tg(env, "sendMessage", {
              chat_id: chat,
              text: "Invalid Job ID."
            });
          } else {
            const format =
              (await env.HORROR_TOPICS.get("SELECTED_FORMAT")) || "short";

            const job = id;

            await dispatchWorkflow(env, "production.yml", {
              action: "story_pack",
              job_id: job,
              topic_title: id,
              format
            });

            await env.HORROR_TOPICS.put(
              "ACTIVE_JOB",
              JSON.stringify({
                job_id: job,
                format,
                next_scene: 1,
                uploaded_count: 0
              })
            );

            await env.HORROR_TOPICS.delete("SELECTED_FORMAT");

            await tg(env, "sendMessage", {
              chat_id: chat,
              text:
                `Approved.\nJob ID: ${job}\n` +
                `Format: ${format.toUpperCase()}\n` +
                `Required clips: ${format === "long" ? 48 : 5}\n\n` +
                "Wait for your story and Flow prompts. Then upload clips here one by one."
            });
          }
        } else if (text) {
          await tg(env, "sendMessage", {
            chat_id: chat,
            text: "Use /help to see available commands."
          });
        }
      }

      if (update.callback_query) {
        const q = update.callback_query;
        const data = q.data || "";
        const [action, id] = data.split(":");

        if (action === "approve" && id) {
          const title = await env.HORROR_TOPICS.get(id);

          if (!title) {
            await tg(env, "answerCallbackQuery", {
              callback_query_id: q.id,
              text: "This topic expired or was already cleared."
            });
          } else {
            const format =
              (await env.HORROR_TOPICS.get("SELECTED_FORMAT")) || "short";

            const job =
              `HOR-${new Date().toISOString().slice(0, 10).replaceAll("-", "")}-${id}`;

            await dispatchWorkflow(env, "production.yml", {
              action: "story_pack",
              job_id: job,
              topic_title: title,
              format
            });

            await env.HORROR_TOPICS.put(
              "ACTIVE_JOB",
              JSON.stringify({
                job_id: job,
                format,
                next_scene: 1,
                uploaded_count: 0
              })
            );

            await env.HORROR_TOPICS.delete("SELECTED_FORMAT");
            await env.HORROR_TOPICS.delete(id);

            await tg(env, "answerCallbackQuery", {
              callback_query_id: q.id,
              text: "Approved — story pack is being created."
            });

            await tg(env, "sendMessage", {
              chat_id: q.message.chat.id,
              text:
                `Approved topic: ${title}\n` +
                `Job ID: ${job}\n` +
                `Format: ${format.toUpperCase()}\n` +
                `Required clips: ${format === "long" ? 48 : 5}\n\n` +
                "Your story and Flow prompts will arrive shortly."
            });
          }
        } else {
          if (id) await env.HORROR_TOPICS.delete(id);

          await tg(env, "answerCallbackQuery", {
            callback_query_id: q.id,
            text: "Skipped."
          });
        }
      }

      return new Response("OK");
    }

    if (u.pathname === "/topic" && request.method === "POST") {
      if (
        request.headers.get("x-topic-ingest-secret") !==
        env.TOPIC_INGEST_SECRET
      ) {
        return new Response("Unauthorized", { status: 401 });
      }

      const b = await request.json();

      if (!b.id || !b.title) {
        return json({ error: "id and title required" }, 400);
      }

      await env.HORROR_TOPICS.put(
        b.id,
        b.title,
        { expirationTtl: 86400 }
      );

      return json({ ok: true });
    }

    return json({ service: "Horror Studio Cloud webhook" });
  }
};
