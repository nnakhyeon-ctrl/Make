import ctypes
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

variable = getattr(sys, '_MEIPASS', None)
if variable:
    folder = Path(variable)
    for location, path in (('TCL_LIBRARY', '_tcl_data'), ('TK_LIBRARY', '_tk_data')):
        try:
            os.environ[location] = str(folder / path)
        except ValueError:
            pass

import tkinter as tk
from tkinter import ttk, messagebox

import pythoncom
import win32com.client
import win32cred

BASE = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
CONFIG = BASE / 'config.json'
PREFIX = 'SAPLoginAutomation:'

FIELDS = (
    ('shared_user_field', '사내 인증 사용자 입력 ID'),
    ('shared_password_field', '사내 인증 암호 입력 ID'),
    ('shared_continue_button', '사내 인증 Continue 버튼 ID'),
    ('duplicate_cancel_radio', '이번 로그인 취소 라디오 ID'),
    ('duplicate_cancel_label', '이번 로그인 취소의 정확한 문구'),
    ('duplicate_confirm_button', '중복 로그인 확인 버튼 ID'),
    ('success_control', '로그인 완료 화면 전용 컨트롤 ID'),
)


def credential(name, password):
    target = PREFIX + name
    if password:
        blob = password.encode('utf-16-le')
        win32cred.CredWrite({
            'Type': win32cred.CRED_TYPE_GENERIC,
            'TargetName': target,
            'UserName': name,
            'CredentialBlob': blob,
            'Persist': win32cred.CRED_PERSIST_LOCAL_MACHINE,
        }, 0)
    else:
        try:
            cred = win32cred.CredRead(target, win32cred.CRED_TYPE_GENERIC)
            blob = cred['CredentialBlob']
            if isinstance(blob, bytes):
                return blob.decode('utf-16-le')
            return blob
        except Exception:
            return None


def engine():
    try:
        return win32com.client.GetObject('SAPGUI').GetScriptingEngine
    except Exception:
        raise RuntimeError('SAP 자동화 연결 실패. SAP 실행 여부, SAP GUI Scripting 설정, 두 프로그램의 실행 권한이 같은지 확인하세요.')


def start_engine(c):
    try:
        return engine()
    except RuntimeError:
        pass
    path = Path(c['saplogon_exe'])
    if not path.is_file():
        raise RuntimeError('SAP 실행 파일 경로를 확인하세요.')
    subprocess.Popen([str(path)])
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        time.sleep(0.5)
        try:
            return engine()
        except RuntimeError:
            pass
    raise RuntimeError('SAP 실행 후 자동화 연결 실패. Scripting 설정과 실행 권한을 확인하세요.')


def find(s, cid):
    try:
        return s.FindById(cid)
    except Exception:
        return False


def ready(s):
    end = time.monotonic() + 45
    while s.Busy and time.monotonic() < end:
        time.sleep(0.2)
    if s.Busy:
        raise RuntimeError('SAP 응답 시간 초과. 재시도하지 않습니다.')


def missing(c):
    result = []
    for k, label in FIELDS:
        if not c.get(k, '').strip() or c.get(k, '').startswith('REPLACE_'):
            result.append(label)
    if not c.get('server_duplicate_dialog_verified', False):
        result.append('두 계정의 서버 중복 로그인 감지 확인')
    return result


def login(c, report):
    absent = missing(c)
    if absent:
        raise RuntimeError('초기 설정 필요:\n• ' + '\n• '.join(absent) + '\n화면 설정 탭에서 설정하세요. SAP 실행/ID 조회는 별도로 사용할 수 있습니다.')

    a = c['accounts']
    secrets = []
    for name in a:
        pw = credential('sap:' + name, None)
        if not pw:
            secrets.append(name)
    shared = credential('shared:' + c['shared_user'], None)
    if not shared:
        secrets.append(c['shared_user'])
    if not all([not secrets]):
        raise RuntimeError('계정 탭에서 세 계정의 비밀번호를 등록하세요.')

    app = start_engine(c)
    occupied = 0

    for index, account in enumerate(a):
        report(str(index + 1) + '번째 계정 로그인 시도 중')
        con = app.OpenConnection(c['connection_name'], True)
        s = con.Children(0)
        ready(s)

        cid = find(s, 'wnd[1]')
        if cid:
            raise RuntimeError('로그인 전 예상하지 못한 창입니다. SAP 화면을 확인하세요.')

        find(s, 'txtRSYST-MANDT').Text = c['client']
        find(s, 'txtRSYST-BNAME').Text = account
        find(s, 'pwdRSYST-BCODE').Text = credential('sap:' + account, None)
        find(s, 'txtRSYST-LANGU').Text = 'KO'
        find(s, 'wnd[0]').SendVKey(0)
        ready(s)

        modal = find(s, 'wnd[1]')
        if modal:
            cancel = find(s, c['duplicate_cancel_radio'])
            if cancel and cancel.Type == 'GuiRadioButton':
                value = cancel.Text.strip()
                if value != c['duplicate_cancel_label'].strip():
                    raise RuntimeError('취소 옵션 문구/유형 불일치. 기존 접속에 영향을 주는 버튼은 누르지 않았습니다.')
                cancel.Select()
                find(s, c['duplicate_confirm_button']).Press()
                ready(s)

                if find(s, 'wnd[0]/usr/txtRSYST-BNAME'):
                    raise RuntimeError('이번 로그인 취소 결과 확인 불가. 자동 진행을 중단했습니다.')

                occupied += 1
                report(str(index + 1) + '번째 계정 사용 중. 이번 시도 취소 완료.')
                con.CloseConnection()
                continue
            elif modal.Text.strip() == c.get('shared_dialog_title', '').strip():
                pass
            else:
                raise RuntimeError('예상하지 못한 인증창입니다. 수동 확인이 필요합니다.')

        if find(s, c.get('shared_user_field', '')):
            find(s, c['shared_user_field']).Text = c['shared_user']
            find(s, c['shared_password_field']).Text = shared
            find(s, c['shared_continue_button']).Press()
            ready(s)

        bar = find(s, 'wnd[0]/sbar')
        if bar and bar.MessageType in ('E', 'A', 'W'):
            raise RuntimeError('SAP 오류 또는 경고입니다. 비밀번호 재시도 없이 중단합니다.')

        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if find(s, c['success_control']):
                report(str(index + 1) + '번째 계정 로그인 완료')
                return
            time.sleep(0.3)
        raise RuntimeError('로그인 완료 확인 시간 초과. SAP 화면을 확인하세요.')

    if occupied == 2:
        raise RuntimeError('두 계정 모두 사용 중이므로 접속하지 않습니다.')


class App:
    def __init__(self, root):
        self.q = queue.Queue()
        self.root = root
        self.running = False
        self.c = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
        root.title('SAP 자동 로그인 · 설정 및 진단')
        root.geometry('860x690')

        tabs = ttk.Notebook(root)
        tabs.pack(fill='both', expand=True, padx=14, pady=3)

        account = ttk.Frame(tabs, padding=14)
        settings = ttk.Frame(tabs, padding=14)
        diagnostics = ttk.Frame(tabs, padding=14)
        tabs.add(account, text='계정 / 실행')
        tabs.add(settings, text='화면 설정')
        tabs.add(diagnostics, text='연결 진단 / 화면 ID')

        self.vars = {}
        names = ('1차 우선 계정', '1차 대체 계정', '2차 사내 인증')
        for i, (label, value) in enumerate(zip(names, list(self.c.get('accounts', [])) + [self.c.get('shared_user', '')])):
            self._entry(account, i * 2, 'id' + str(i), label + ' ID', str(value), '')
            self._entry(account, i * 2 + 1, 'pw' + str(i), '새 비밀번호', '', '*')

        ttk.Label(account, text='암호 칸을 비우면 기존 암호 유지 · ID 변경 시 새 암호 입력\nWindows 자격 증명 저장소 사용 · SAP 서버의 암호 자체를 변경하지 않습니다.').grid(row=6, columnspan=2, sticky='w', pady=15)

        ttk.Button(account, text='계정 / 설정 저장', command=self.save).grid(row=7, column=0, pady=8)
        ttk.Button(account, text='저장 후 자동 로그인', command=self.start_login).grid(row=7, column=1, pady=8)

        row = 0
        for key, title in (('connection_name', 'SAP Logon 연결 이름'), ('saplogon_exe', 'SAP 실행 파일'), ('shared_dialog_title', '사내 인증창 제목')):
            self._entry(settings, row, key, title, str(self.c.get(key, '')), '')
            row += 1

        self.verified = tk.BooleanVar(value=self.c.get('server_duplicate_dialog_verified', False))
        ttk.Checkbutton(settings, text='두 계정의 중복 로그인 경고와 이번 로그인 취소 동작을 실제 확인함', variable=self.verified).grid(row=row, columnspan=2, sticky='w')
        row += 1
        ttk.Button(settings, text='설정 저장', command=self.save).grid(row=row, column=0, pady=8)
        row += 1

        for key, title in FIELDS:
            self._entry(settings, row, key, title, str(self.c.get(key, '')), '')
            row += 1

        ttk.Label(settings, text='ID는 wnd[1]/usr/... 형태로 입력합니다. 기존 세션 종료 옵션을 지정하지 마세요.', anchor='w').grid(row=row, columnspan=2, sticky='w')

        ttk.Label(diagnostics, text='SAP 실행 → SAP에서 원하는 화면 열기 → 화면 ID 읽기\n이 기능은 입력값/암호를 읽지 않습니다. 여러 세션이 있으면 모두 표시합니다.', anchor='w', pady=10).grid(row=0, columnspan=2, sticky='w')

        ttk.Button(diagnostics, text='SAP Logon 실행', command=self.launch).grid(row=1, column=0, pady=8)
        ttk.Button(diagnostics, text='현재 화면 ID 읽기', command=lambda: self.job(self.inspect)).grid(row=1, column=1, pady=8)

        self.output = tk.Text(diagnostics, height=20, wrap='none')
        self.output.grid(row=2, columnspan=2, sticky='ew', pady=10)

        ttk.Button(diagnostics, text='ID 목록을 클립보드에 복사', command=self.copy).grid(row=3, column=0, pady=8)

        ttk.Label(diagnostics, text='계정 저장 후 초기 화면 설정을 확인하세요. 미설정 상태에서도 SAP 실행과 ID 조회는 가능합니다.', anchor='w', pady=11).grid(row=12, columnspan=2, sticky='w')

        self.status = tk.StringVar()
        ttk.Label(root, textvariable=self.status, wraplength=820, padding=15).pack(fill='x')

        root.after(150, self.poll)
        root.protocol('WM_DELETE_WINDOW', self.close)

    def _entry(self, parent, row, key, label, value, show):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', pady=5)
        var = tk.StringVar(value=value)
        ttk.Entry(parent, textvariable=var, show=show, width=65).grid(row=row, column=1, sticky='ew', padx=8)
        self.vars[key] = var

    def save(self):
        if self.running:
            return
        try:
            disk = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
            updated = dict(self.c)

            if disk != self.c:
                raise RuntimeError('설정 파일이 변경되었습니다. 프로그램을 다시 여세요.')

            ids = [self.vars['id' + str(i)].get().strip() for i in range(3)]
            pws = [self.vars['pw' + str(i)].get() for i in range(3)]

            if not all(ids) or ids[0].upper() == ids[1].upper():
                raise RuntimeError('ID를 모두 입력하고 1차 계정 두 개를 서로 다르게 지정하세요.')

            old = list(updated.get('accounts', [])) + [updated.get('shared_user', '')]
            names = ['sap:', 'sap:', 'shared:']

            need_pw = []
            for i in range(3):
                n = names[i] + ids[i]
                before = names[i] + old[i] if i < len(old) else ''
                if n != before or not credential(n, None):
                    if not pws[i].strip():
                        need_pw.append(ids[i])
            if need_pw:
                raise RuntimeError('새 계정 또는 최초 등록 계정의 비밀번호를 입력하세요.')

            updated['accounts'] = [ids[0], ids[1]]
            updated['shared_user'] = ids[2]
            updated['server_duplicate_dialog_verified'] = self.verified.get()

            for k, _ in (('connection_name', ''), ('saplogon_exe', ''), ('shared_dialog_title', '')):
                updated[k] = self.vars[k].get().strip()

            for k, _ in FIELDS:
                if k in self.vars:
                    updated[k] = self.vars[k].get().strip()

            changed = []
            for i in range(3):
                if pws[i].strip():
                    n = names[i] + ids[i]
                    try:
                        credential(n, pws[i])
                    except Exception as e:
                        raise RuntimeError(f'암호 저장 실패 ({ids[i]}): {e}')
                    changed.append(n)

            temp = CONFIG.with_suffix('.json.tmp')
            try:
                temp.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')
                os.replace(str(temp), str(CONFIG))
            except Exception as e:
                for n in changed:
                    try:
                        win32cred.CredDelete(PREFIX + n, win32cred.CRED_TYPE_GENERIC)
                    except Exception:
                        pass
                if temp.exists():
                    try:
                        temp.unlink()
                    except Exception:
                        pass
                raise RuntimeError(f'설정 파일 저장 실패: {e}')

            written = self.c != updated
            self.c = updated

            msg = '저장 완료. '
            if old[:2] != [ids[0], ids[1]]:
                msg += '새 1차 계정의 중복 접속 동작을 다시 확인하세요. '
            absent = missing(updated)
            if absent:
                msg += '초기 설정 남음: ' + str(len(absent)) + '개'
            self.status.set(msg)

        except RuntimeError as e:
            self.status.set(str(e))
        except Exception as e:
            self.status.set(f'저장 실패: {type(e).__name__}: {e}')
            messagebox.showerror('저장 실패', f'설정/암호 저장 실패.\n\n원인: {type(e).__name__}: {e}\n\n쓰기 권한을 확인하세요.')

    def launch(self):
        if self.running:
            return
        path = self.vars.get('saplogon_exe', self.vars.get('saplogon_exe'))
        if path:
            path = path.get().strip()
        else:
            path = self.c.get('saplogon_exe', '')
        if not Path(path).is_file():
            messagebox.showerror('SAP 실행', 'SAP 실행 파일 경로가 올바르지 않습니다.')
            return
        try:
            subprocess.Popen([path])
            self.status.set('SAP 실행 요청 완료. SAP에서 공용 ID 창을 연 뒤 화면 ID 읽기를 누르세요.')
        except Exception:
            self.status.set('SAP 실행 실패. 파일 경로와 실행 권한을 확인하세요.')

    def inspect(self):
        app = engine()
        lines = []

        def walk(node):
            lines.append(node.Id + ' | ' + node.Type)
            if node.ContainerType:
                for k in range(node.Children.Count):
                    walk(node.Children(k))

        for i in range(app.Children.Count):
            con = app.Children(i)
            for j in range(con.Children.Count):
                s = con.Children(j)
                if not s.Busy:
                    walk(s)

        if lines:
            self.q.put(('ids', '\n'.join(lines)))
        else:
            self.q.put(('error', '열린 SAP 세션이 없습니다. SAP에서 시스템 연결을 여세요.'))

    def start_login(self):
        if not self.save():
            pass
        self.job(lambda: login(self.c, lambda t: self.q.put(('status', t))))

    def job(self, action):
        if self.running:
            return
        self.running = True
        self.status.set('처리 중…')

        def work():
            initialized = False
            try:
                pythoncom.CoInitialize()
                initialized = True
                action()
            except Exception as e:
                if isinstance(e, RuntimeError):
                    self.q.put(('error', str(e)))
                else:
                    self.q.put(('error', 'SAP 처리 실패. Scripting 설정과 SAP 화면을 확인하세요.'))
            finally:
                self.q.put(('done', ''))
                if initialized:
                    pythoncom.CoUninitialize()

        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            kind, text = self.q.get_nowait()
            if kind == 'done':
                self.running = False
            elif kind == 'ids':
                self.output.delete('1.0', 'end')
                self.output.insert('1.0', text)
                self.status.set('화면 ID 조회 완료. 목록을 복사해 설정에 사용할 수 있습니다.')
            elif kind == 'error':
                self.status.set('처리 중단. 오류 창 내용을 확인하세요.')
                messagebox.showerror('확인 필요', text)
            elif kind == 'status':
                self.status.set(text)
        except queue.Empty:
            pass
        self.root.after(150, self.poll)

    def copy(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.output.get('1.0', 'end-1c'))
        self.status.set('ID 목록 복사 완료. 채팅에 붙여 넣으세요.')

    def close(self):
        if self.running:
            messagebox.showinfo('처리 중', '처리가 끝난 뒤 닫으세요.')
            return
        self.root.destroy()


def main():
    if '--self-test' in sys.argv:
        result = {'gui_initialized': False, 'sap_login_tested': False}
        try:
            test_root = tk.Tk()
            test_root.withdraw()
            test_app = App(test_root)
            test_root.update()
            result['gui_initialized'] = True
            result['account_ids_loaded'] = (
                test_app.vars.get('id0') and test_app.vars['id0'].get() == '50MM-01'
                and test_app.vars.get('id1') and test_app.vars['id1'].get() == '50MM-07'
            )
            test_root.destroy()
        except Exception as exc:
            result['error_type'] = type(exc).__name__
            result['error_detail'] = str(exc)
        (BASE / 'self-test-result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        return

    try:
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        kernel.CreateMutexW.restype = ctypes.c_void_p
        handle = kernel.CreateMutexW(None, False, 'Local\\SAPLoginEditorV2')
        if ctypes.get_last_error() == 183:
            messagebox.showinfo('실행 확인', '프로그램이 이미 실행 중이거나 실행 잠금을 만들지 못했습니다.')
            return
    except Exception:
        pass

    try:
        root = tk.Tk()
        App(root)
        root.mainloop()
    except Exception:
        messagebox.showerror('시작 실패', 'EXE 옆의 config.json 파일을 확인하세요.')


if __name__ == '__main__':
    main()
