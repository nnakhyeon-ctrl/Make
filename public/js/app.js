import { MENU } from "./menu-data.js";
import { initRouter } from "./router.js";

function renderSidebar() {
  const sidebar = document.getElementById("sidebar");

  sidebar.innerHTML = MENU.map((section, gi) => `
    <div class="menu-group" data-group="${gi}">
      <button type="button" class="menu-group-title">
        <span>${section.group}</span>
        <span class="chevron">▾</span>
      </button>
      <ul class="menu-list">
        ${section.items.map(item => `
          <li>
            <a href="#/${item.route}" class="menu-link" data-route="${item.route}">
              ${item.label}
            </a>
          </li>
        `).join("")}
      </ul>
    </div>
  `).join("");

  sidebar.querySelectorAll(".menu-group-title").forEach(btn => {
    btn.addEventListener("click", () => {
      btn.closest(".menu-group").classList.toggle("collapsed");
    });
  });

  sidebar.addEventListener("click", (e) => {
    const link = e.target.closest(".menu-link");
    if (!link) return;
    sidebar.querySelectorAll(".menu-link.active").forEach(el => el.classList.remove("active"));
    link.classList.add("active");
  });
}

renderSidebar();
initRouter();
