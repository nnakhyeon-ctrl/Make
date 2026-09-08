export async function onRequestGet({ env }) {
  const { results } = await env.DB
    .prepare("SELECT * FROM delivery ORDER BY id DESC LIMIT 200")
    .all();
  return Response.json(results);
}

export async function onRequestPost({ request, env }) {
  const body = await request.json();
  const { vendor_code, vendor_name, item_code, item_name, qty, unit, delivery_date } = body;

  if (!vendor_code || !vendor_name || !item_code || !item_name || !qty || !delivery_date) {
    return new Response("필수 항목이 누락되었습니다.", { status: 400 });
  }

  const result = await env.DB.prepare(
    `INSERT INTO delivery (vendor_code, vendor_name, item_code, item_name, qty, unit, delivery_date)
     VALUES (?, ?, ?, ?, ?, ?, ?)`
  ).bind(vendor_code, vendor_name, item_code, item_name, qty, unit ?? null, delivery_date).run();

  return Response.json({ id: result.meta.last_row_id }, { status: 201 });
}
