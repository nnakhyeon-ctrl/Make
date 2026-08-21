#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
유상사급 일별 출고수량 채우기 - 화면(GUI) 버전
--------------------------------------------------
명령어를 입력하지 않고, 파일 선택 창에서 템플릿/원본 파일을 고르고
"실행" 버튼만 누르면 결과 파일이 만들어진다.

실행: 이 파일을 더블클릭하거나  python gui.pyw  로 실행한다.
(파이썬을 python.org 기본 옵션으로 설치했다면 .pyw 파일은 보통
 콘솔 창 없이 pythonw로 바로 실행되도록 연결되어 있다.)

같은 폴더의 fill_daily_shipment.py 가 반드시 있어야 한다(핵심 로직을
그대로 가져다 쓴다 — 계산 방식은 콘솔 버전과 완전히 동일하다).
"""

import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fill_daily_shipment as core


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("유상사급 일별 출고수량 채우기")
        self.geometry("700x520")
        self.resizable(True, True)

        self.template_path = tk.StringVar()
        self.source_path = tk.StringVar()
        self.same_file = tk.BooleanVar(value=False)
        self.last_output = None

        pad = {"padx": 10, "pady": 6}

        frm = ttk.Frame(self)
        frm.pack(fill="x", **pad)

        ttk.Label(frm, text="① 템플릿 파일 (유상사급 시트가 든 xlsx)").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.template_path).grid(row=1, column=0, sticky="ew")
        ttk.Button(frm, text="찾아보기...", command=self.pick_template).grid(row=1, column=1, padx=(6, 0))

        ttk.Checkbutton(
            frm, text="원본(Sheet1)이 템플릿과 같은 파일 안에 있음",
            variable=self.same_file, command=self.toggle_same_file,
        ).grid(row=2, column=0, sticky="w", pady=(10, 0))

        ttk.Label(frm, text="② 원본 파일 (Sheet1 출고 데이터가 든 xlsx)").grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.source_entry = ttk.Entry(frm, textvariable=self.source_path)
        self.source_entry.grid(row=4, column=0, sticky="ew")
        self.source_btn = ttk.Button(frm, text="찾아보기...", command=self.pick_source)
        self.source_btn.grid(row=4, column=1, padx=(6, 0))

        frm.columnconfigure(0, weight=1)

        self.run_btn = ttk.Button(self, text="실행", command=self.on_run)
        self.run_btn.pack(pady=10)

        self.log = scrolledtext.ScrolledText(self, height=18, font=("Consolas", 10))
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log.configure(state="disabled")

        btnrow = ttk.Frame(self)
        btnrow.pack(fill="x", padx=10, pady=(0, 10))
        self.open_folder_btn = ttk.Button(btnrow, text="결과 파일이 있는 폴더 열기", command=self.open_result_folder, state="disabled")
        self.open_folder_btn.pack(side="left")

    def toggle_same_file(self):
        if self.same_file.get():
            self.source_path.set("")
            self.source_entry.configure(state="disabled")
            self.source_btn.configure(state="disabled")
        else:
            self.source_entry.configure(state="normal")
            self.source_btn.configure(state="normal")

    def pick_template(self):
        path = filedialog.askopenfilename(
            title="템플릿 파일 선택 (유상사급 시트)",
            filetypes=[("Excel 파일", "*.xlsx *.xls *.XLSX"), ("모든 파일", "*.*")],
        )
        if path:
            self.template_path.set(path)

    def pick_source(self):
        path = filedialog.askopenfilename(
            title="원본 파일 선택 (Sheet1)",
            filetypes=[("Excel 파일", "*.xlsx *.xls *.XLSX"), ("모든 파일", "*.*")],
        )
        if path:
            self.source_path.set(path)

    def append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def on_run(self):
        tpl = self.template_path.get().strip()
        src = None if self.same_file.get() else (self.source_path.get().strip() or None)

        if not tpl:
            messagebox.showwarning("알림", "① 템플릿 파일을 먼저 선택하세요.")
            return
        if not self.same_file.get() and not src:
            messagebox.showwarning("알림", "② 원본 파일을 선택하거나, 같은 파일이면 체크박스를 켜세요.")
            return

        self.run_btn.configure(state="disabled")
        self.open_folder_btn.configure(state="disabled")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.append_log("처리 중...")

        threading.Thread(target=self._run_worker, args=(tpl, src), daemon=True).start()

    def _run_worker(self, tpl, src):
        try:
            lines, out_path = core.run_fill(tpl, source_path=src)
            self.after(0, self._on_done, lines, out_path, None)
        except Exception as e:  # noqa: BLE001 - 사용자에게 원인을 그대로 보여줘야 함
            self.after(0, self._on_done, None, None, e)

    def _on_done(self, lines, out_path, error):
        self.run_btn.configure(state="normal")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        if error is not None:
            self.log.insert("end", f"오류가 발생했습니다:\n{error}\n")
            self.log.configure(state="disabled")
            messagebox.showerror("오류", str(error))
            return
        self.log.insert("end", "\n".join(lines))
        self.log.configure(state="disabled")
        self.last_output = out_path
        self.open_folder_btn.configure(state="normal")
        messagebox.showinfo("완료", f"결과 파일을 저장했습니다:\n{out_path}")

    def open_result_folder(self):
        if not self.last_output:
            return
        folder = os.path.dirname(os.path.abspath(self.last_output))
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)  # noqa: S606 - 사용자가 직접 만든 결과 폴더를 여는 것뿐
            elif sys.platform == "darwin":
                subprocess.run(["open", folder], check=False)
            else:
                subprocess.run(["xdg-open", folder], check=False)
        except OSError as e:
            messagebox.showerror("오류", f"폴더를 열지 못했습니다: {e}")


if __name__ == "__main__":
    App().mainloop()
