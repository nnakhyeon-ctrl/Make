export async function render(root) {
  root.innerHTML = `
    <h2>납입등록</h2>
    <form id="deliveryForm" class="form-row">
      <input name="vendor_code" placeholder="업체코드" required />
      <input name="vendor_name" placeholder="업체명" required />
      <input name="item_code" placeholder="품번" required />
      <input name="item_name" placeholder="품명" required />
      <input name="qty" type="number" placeholder="수량" required />
      <input name="unit" placeholder="단위" />
      <input name="delivery_date" type="date" required />
      <button type="submit">등록</button>
    </form>

    <table class="grid">
      <thead>
        <tr>
          <th>ID</th><th>업체코드</th><th>업체명</th><th>품번</th><th>품명</th>
          <th>수량</th><th>단위</th><th>납입일</th><th>상태</th><th>삭제</th>
        </tr>
      </thead>
      <tbody id="deliveryBody"></tbody>
    </table>
  `;

  const form = root.querySelector("#deliveryForm");
  const body = root.querySelector("#deliveryBody");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    data.qty = Number(data.qty);

    const res = await fetch("/api/delivery", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!res.ok) {
      alert("등록 실패: " + (await res.text()));
      return;
    }

    form.reset();
    loadList();
  });

  body.addEventListener("click", async (e) => {
    const btn = e.target.closest(".btn-delete");
    if (!btn) return;
    if (!confirm("삭제하시겠습니까?")) return;

    await fetch(`/api/delivery/${btn.dataset.id}`, { method: "DELETE" });
    loadList();
  });

  async function loadList() {
    const res = await fetch("/api/delivery");
    const rows = await res.json();

    body.innerHTML = rows.map(r => `
      <tr>
        <td>${r.id}</td>
        <td>${r.vendor_code}</td>
        <td>${r.vendor_name}</td>
        <td>${r.item_code}</td>
        <td>${r.item_name}</td>
        <td>${r.qty}</td>
        <td>${r.unit ?? ""}</td>
        <td>${r.delivery_date}</td>
        <td>${r.status}</td>
        <td><button class="btn-delete" data-id="${r.id}">삭제</button></td>
      </tr>
    `).join("");
  }

  loadList();
}
