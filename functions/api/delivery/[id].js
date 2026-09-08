export async function onRequestPut({ params, request, env }) {
  const body = await request.json();

  await env.DB.prepare(
    `UPDATE delivery SET qty = ?, status = ? WHERE id = ?`
  ).bind(body.qty, body.status, params.id).run();

  return Response.json({ ok: true });
}

export async function onRequestDelete({ params, env }) {
  await env.DB.prepare(`DELETE FROM delivery WHERE id = ?`).bind(params.id).run();
  return new Response(null, { status: 204 });
}
