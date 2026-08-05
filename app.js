(function () {
  "use strict";

  const STORAGE_KEY = "my-calendar-data-v1";
  const WEEKDAY_NAMES = ["일", "월", "화", "수", "목", "금", "토"];

  const state = {
    viewYear: new Date().getFullYear(),
    viewMonth: new Date().getMonth(),
    selectedKey: formatKey(new Date()),
    data: loadData(),
    activeTab: "todo",
  };

  const el = {
    currentMonth: document.getElementById("currentMonth"),
    calendarGrid: document.getElementById("calendarGrid"),
    prevMonth: document.getElementById("prevMonth"),
    nextMonth: document.getElementById("nextMonth"),
    todayBtn: document.getElementById("todayBtn"),
    selectedDateLabel: document.getElementById("selectedDateLabel"),
    selectedDateSub: document.getElementById("selectedDateSub"),
    tabBtns: document.querySelectorAll(".tab-btn"),
    todoTab: document.getElementById("todoTab"),
    memoTab: document.getElementById("memoTab"),
    todoForm: document.getElementById("todoForm"),
    todoInput: document.getElementById("todoInput"),
    todoList: document.getElementById("todoList"),
    todoEmptyHint: document.getElementById("todoEmptyHint"),
    todoProgress: document.getElementById("todoProgress"),
    memoText: document.getElementById("memoText"),
    saveIndicator: document.getElementById("saveIndicator"),
    charCount: document.getElementById("charCount"),
  };

  function loadData() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      console.warn("데이터를 불러오지 못했습니다.", e);
      return {};
    }
  }

  function saveData() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.data));
  }

  function formatKey(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }

  function getDayEntry(key) {
    return state.data[key] || { todos: [], memo: "" };
  }

  function ensureDayEntry(key) {
    if (!state.data[key]) {
      state.data[key] = { todos: [], memo: "" };
    }
    return state.data[key];
  }

  function pruneIfEmpty(key) {
    const entry = state.data[key];
    if (entry && entry.todos.length === 0 && !entry.memo.trim()) {
      delete state.data[key];
    }
  }

  function renderCalendar() {
    const { viewYear, viewMonth } = state;
    el.currentMonth.textContent = `${viewYear}년 ${viewMonth + 1}월`;

    const firstOfMonth = new Date(viewYear, viewMonth, 1);
    const startOffset = firstOfMonth.getDay();
    const gridStart = new Date(viewYear, viewMonth, 1 - startOffset);

    const todayKey = formatKey(new Date());

    el.calendarGrid.innerHTML = "";
    const totalCells = 42;

    for (let i = 0; i < totalCells; i++) {
      const cellDate = new Date(gridStart);
      cellDate.setDate(gridStart.getDate() + i);
      const key = formatKey(cellDate);
      const isOtherMonth = cellDate.getMonth() !== viewMonth;
      const dow = cellDate.getDay();

      const cell = document.createElement("div");
      cell.className = "day-cell";
      if (isOtherMonth) cell.classList.add("other-month");
      if (dow === 0) cell.classList.add("sunday");
      if (dow === 6) cell.classList.add("saturday");
      if (key === todayKey) cell.classList.add("is-today");
      if (key === state.selectedKey) cell.classList.add("is-selected");
      cell.dataset.key = key;

      const dayNum = document.createElement("div");
      dayNum.className = "day-num";
      dayNum.textContent = cellDate.getDate();
      cell.appendChild(dayNum);

      const entry = state.data[key];
      const markerWrap = document.createElement("div");
      markerWrap.className = "day-markers";
      if (entry) {
        const pending = entry.todos.filter((t) => !t.done).length;
        if (entry.todos.length > 0) {
          const m = document.createElement("span");
          m.className = "marker todo";
          markerWrap.appendChild(m);
        }
        if (entry.memo && entry.memo.trim()) {
          const m = document.createElement("span");
          m.className = "marker memo";
          markerWrap.appendChild(m);
        }
        if (pending > 0) {
          const countBadge = document.createElement("span");
          countBadge.className = "todo-count";
          countBadge.textContent = pending;
          cell.appendChild(countBadge);
        }
      }
      cell.appendChild(markerWrap);

      cell.addEventListener("click", () => selectDate(key));
      el.calendarGrid.appendChild(cell);
    }
  }

  function selectDate(key) {
    state.selectedKey = key;
    const [y, m] = key.split("-").map(Number);
    if (y !== state.viewYear || m - 1 !== state.viewMonth) {
      state.viewYear = y;
      state.viewMonth = m - 1;
    }
    renderCalendar();
    renderSidePanel();
  }

  function renderSidePanel() {
    const key = state.selectedKey;
    const [y, m, d] = key.split("-").map(Number);
    const dateObj = new Date(y, m - 1, d);
    el.selectedDateLabel.textContent = `${m}월 ${d}일 ${WEEKDAY_NAMES[dateObj.getDay()]}요일`;
    const todayKey = formatKey(new Date());
    el.selectedDateSub.textContent = key === todayKey ? "오늘" : "";

    renderTodos();
    renderMemo();
  }

  function renderTodos() {
    const entry = getDayEntry(state.selectedKey);
    el.todoList.innerHTML = "";

    if (entry.todos.length === 0) {
      el.todoEmptyHint.style.display = "block";
      el.todoProgress.textContent = "";
      return;
    }
    el.todoEmptyHint.style.display = "none";

    entry.todos.forEach((todo) => {
      const li = document.createElement("li");
      li.className = "todo-item" + (todo.done ? " done" : "");

      const check = document.createElement("button");
      check.type = "button";
      check.className = "todo-check";
      check.setAttribute("aria-label", "완료 토글");
      check.textContent = todo.done ? "✓" : "";
      check.addEventListener("click", () => toggleTodo(todo.id));

      const text = document.createElement("span");
      text.className = "todo-text";
      text.textContent = todo.text;

      const del = document.createElement("button");
      del.type = "button";
      del.className = "todo-delete";
      del.setAttribute("aria-label", "삭제");
      del.textContent = "✕";
      del.addEventListener("click", () => deleteTodo(todo.id));

      li.appendChild(check);
      li.appendChild(text);
      li.appendChild(del);
      el.todoList.appendChild(li);
    });

    const done = entry.todos.filter((t) => t.done).length;
    el.todoProgress.textContent = `${done} / ${entry.todos.length} 완료`;
  }

  function renderMemo() {
    const entry = getDayEntry(state.selectedKey);
    el.memoText.value = entry.memo || "";
    el.charCount.textContent = `${(entry.memo || "").length}자`;
    el.saveIndicator.classList.remove("show");
  }

  function toggleTodo(id) {
    const entry = ensureDayEntry(state.selectedKey);
    const todo = entry.todos.find((t) => t.id === id);
    if (todo) todo.done = !todo.done;
    saveData();
    renderTodos();
    renderCalendar();
  }

  function deleteTodo(id) {
    const entry = ensureDayEntry(state.selectedKey);
    entry.todos = entry.todos.filter((t) => t.id !== id);
    pruneIfEmpty(state.selectedKey);
    saveData();
    renderTodos();
    renderCalendar();
  }

  function addTodo(text) {
    const trimmed = text.trim();
    if (!trimmed) return;
    const entry = ensureDayEntry(state.selectedKey);
    entry.todos.push({ id: cryptoId(), text: trimmed, done: false });
    saveData();
    renderTodos();
    renderCalendar();
  }

  function cryptoId() {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  }

  let memoSaveTimer = null;
  function handleMemoInput() {
    const value = el.memoText.value;
    el.charCount.textContent = `${value.length}자`;

    const entry = ensureDayEntry(state.selectedKey);
    entry.memo = value;

    clearTimeout(memoSaveTimer);
    memoSaveTimer = setTimeout(() => {
      pruneIfEmpty(state.selectedKey);
      saveData();
      renderCalendar();
      el.saveIndicator.classList.add("show");
      setTimeout(() => el.saveIndicator.classList.remove("show"), 1200);
    }, 400);
  }

  function switchTab(tab) {
    state.activeTab = tab;
    el.tabBtns.forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tab);
    });
    el.todoTab.classList.toggle("hidden", tab !== "todo");
    el.memoTab.classList.toggle("hidden", tab !== "memo");
  }

  function changeMonth(delta) {
    let newMonth = state.viewMonth + delta;
    let newYear = state.viewYear;
    if (newMonth < 0) {
      newMonth = 11;
      newYear -= 1;
    } else if (newMonth > 11) {
      newMonth = 0;
      newYear += 1;
    }
    state.viewYear = newYear;
    state.viewMonth = newMonth;
    renderCalendar();
  }

  function goToday() {
    const today = new Date();
    state.viewYear = today.getFullYear();
    state.viewMonth = today.getMonth();
    selectDate(formatKey(today));
  }

  function bindEvents() {
    el.prevMonth.addEventListener("click", () => changeMonth(-1));
    el.nextMonth.addEventListener("click", () => changeMonth(1));
    el.todayBtn.addEventListener("click", goToday);

    el.tabBtns.forEach((btn) => {
      btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });

    el.todoForm.addEventListener("submit", (e) => {
      e.preventDefault();
      addTodo(el.todoInput.value);
      el.todoInput.value = "";
      el.todoInput.focus();
    });

    el.memoText.addEventListener("input", handleMemoInput);
  }

  function init() {
    bindEvents();
    renderCalendar();
    renderSidePanel();
  }

  init();
})();
