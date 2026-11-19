const json = (obj, status=200) => new Response(JSON.stringify(obj), {status, headers:{"content-type":"application/json"}});
async function tg(env, method, body) {
  const r = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(body)});
  if (!r.ok) throw new Error(`Telegram ${method}: ${r.status} ${await r.text()}`);
  return r.json();
}
async function dispatchWorkflow(env, workflow, inputs={}) {
  const url = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${workflow}/dispatches`;
  const r = await fetch(url,{method:"POST",headers:{"authorization":`Bearer ${env.GITHUB_TOKEN}`,"accept":"application/vnd.github+json","x-github-api-version":"2022-11-28","content-type":"application/json"},body:JSON.stringify({ref:env.GITHUB_REF||"main",inputs})});
  if (!r.ok) throw new Error(`GitHub dispatch failed: ${r.status} ${await r.text()}`);
}
export default {
 async fetch(request, env) {
  const u=new URL(request.url);
  if (u.pathname.startsWith("/telegram/")) {
   if (u.pathname !== `/telegram/${env.TELEGRAM_WEBHOOK_SECRET}`) return new Response("Not found",{status:404});
   if (request.method !== "POST") return new Response("OK");
   const update=await request.json();
   if (update.message) {
    const m=update.message, chat=m.chat.id, text=(m.text||"").trim();
    if (!env.ALLOWED_TELEGRAM_CHAT_ID || String(chat)!==String(env.ALLOWED_TELEGRAM_CHAT_ID)) return new Response("OK");
    if (text==="/start"||text==="/help") await tg(env,"sendMessage",{chat_id:chat,text:"Horror Studio V4\n\n/trending — run topic discovery from GitHub Actions\n/approve JOB_ID — start story pack workflow for an existing approved job ID\n\nTrending cards require your approval. Flow clips are generated manually and uploaded to Drive INBOX/JOB_ID/."});
    else if (text==="/trending") { await dispatchWorkflow(env,"topic-scout.yml"); await tg(env,"sendMessage",{chat_id:chat,text:"Topic scouting started. I will send approval cards here when candidates are ready."}); }
    else if (text==="/status") await tg(env,"sendMessage",{chat_id:chat,text:`Check the latest cloud job here: https://github.com/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions`});
    else if (text.startsWith("/approve ")) { const id=text.split(/\s+/)[1]; await dispatchWorkflow(env,"production.yml",{action:"story_pack",job_id:id,topic_title:id,format:"short"}); await tg(env,"sendMessage",{chat_id:chat,text:`Approved. Story pack workflow dispatched for ${id}.`}); }
    else await tg(env,"sendMessage",{chat_id:chat,text:"Use /help. Topic discovery runs from GitHub Actions; approve a candidate using its button."});
   }
   if (update.callback_query) {
    const q=update.callback_query, data=q.data||"", [action,id]=data.split(":");
    if (action==="approve" && id) {
      const title=await env.HORROR_TOPICS.get(id);
      if (!title) await tg(env,"answerCallbackQuery",{callback_query_id:q.id,text:"This topic expired or was already cleared."});
      else { const job=`HOR-${new Date().toISOString().slice(0,10).replaceAll("-","")}-${id}`; await dispatchWorkflow(env,"production.yml",{action:"story_pack",job_id:job,topic_title:title,format:"short"}); await tg(env,"answerCallbackQuery",{callback_query_id:q.id,text:"Approved — story pack is being created."}); await tg(env,"sendMessage",{chat_id:q.message.chat.id,text:`Approved topic: ${title}\nJob ID: ${job}\nA story + Flow prompt pack will arrive shortly. No video is generated until you create clips in Flow.`}); await env.HORROR_TOPICS.delete(id); }
    } else { if(id) await env.HORROR_TOPICS.delete(id); await tg(env,"answerCallbackQuery",{callback_query_id:q.id,text:"Skipped."}); }
   }
   return new Response("OK");
  }
  if (u.pathname==="/topic" && request.method==="POST") {
   if (request.headers.get("x-topic-ingest-secret") !== env.TOPIC_INGEST_SECRET) return new Response("Unauthorized",{status:401});
   const b=await request.json(); if(!b.id||!b.title) return json({error:"id and title required"},400);
   await env.HORROR_TOPICS.put(b.id,b.title,{expirationTtl:86400}); return json({ok:true});
  }
  return json({service:"Horror Studio V4 webhook"});
 }
};
