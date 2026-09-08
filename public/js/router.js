const routes = {
  "vendor/delivery": () => import("./pages/delivery.js"),
  "purchase/delivery": () => import("./pages/delivery.js"),
  // 새 화면이 완성될 때마다 여기에 한 줄씩 추가
  // "vendor/statement": () => import("./pages/vendor-statement.js"),
};

export function initRouter() {
  window.addEventListener("hashchange", render);
  render();
}

async function render() {
  const route = location.hash.replace(/^#\//, "") || "";
  const content = document.getElementById("content");
  const loader = routes[route];

  if (!loader) {
    content.innerHTML = `<div class="placeholder">준비 중인 화면입니다: ${route || "(선택 없음)"}</div>`;
    return;
  }

  const mod = await loader();
  content.innerHTML = "";
  mod.render(content, route);
}
