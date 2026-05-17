import ctypes
import re
import time
import threading
import sys
import tkinter as tk
from tkinter import messagebox, ttk

try:
    import pygetwindow as gw
    import pyperclip
except Exception:
    gw = None
    pyperclip = None


def check_deps():
    if gw is None or pyperclip is None:
        messagebox.showerror(
            "Missing dependencies",
            "Required packages not found. Please install:\n\npip install pygetwindow pyperclip",
        )
        return False
    return True


SW_RESTORE = 9
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102
WM_PASTE = 0x0302

VK_MAPPING = {
    '`': 0xC0,
    'tilde': 0xC0,
    'backquote': 0xC0,
    '/': 0xBF,
    'slash': 0xBF,
    'space': 0x20,
    ' ': 0x20,
    'enter': 0x0D,
    'return': 0x0D,
    'tab': 0x09,
    'esc': 0x1B,
    'escape': 0x1B,
    'backspace': 0x08,
    'insert': 0x2D,
    'delete': 0x2E,
    'home': 0x24,
    'end': 0x23,
    'pageup': 0x21,
    'pagedown': 0x22,
    'left': 0x25,
    'up': 0x26,
    'right': 0x27,
    'down': 0x28,
    'shift': 0x10,
    'ctrl': 0x11,
    'control': 0x11,
    'alt': 0x12,
    'f1': 0x70,
    'f2': 0x71,
    'f3': 0x72,
    'f4': 0x73,
    'f5': 0x74,
    'f6': 0x75,
    'f7': 0x76,
    'f8': 0x77,
    'f9': 0x78,
    'f10': 0x79,
    'f11': 0x7A,
    'f12': 0x7B,
    'f13': 0x7C,
    'f14': 0x7D,
    'f15': 0x7E,
    'f16': 0x7F,
    'f17': 0x80,
    'f18': 0x81,
    'f19': 0x82,
    'f20': 0x83,
    'f21': 0x84,
    'f22': 0x85,
    'f23': 0x86,
    'f24': 0x87,
}

EXTENDED_KEYS = {
    0x1C, 0x1D, 0x1E, 0x1F, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25,
    0x26, 0x27, 0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F,
    0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39,
    0x5B, 0x5C, 0x5D, 0x5E, 0x5F,
}


def normalize_title(title):
    return (title or '').strip().lower()


def is_admin_tool_title(title):
    title = (title or '').lower()
    return 'admin tool' in title or 'chivalry 2 admin tool' in title


def find_window(title_substring):
    title_substring = (title_substring or '').strip()
    if not title_substring:
        return None

    search = title_substring.lower().strip()
    all_windows = gw.getAllWindows()
    if not all_windows:
        return None

    candidates = [w for w in all_windows if search in normalize_title(w.title)]
    if not candidates:
        return None

    candidates = [w for w in candidates if not is_admin_tool_title(w.title)] or candidates

    exact = [w for w in candidates if normalize_title(w.title) == search]
    if exact:
        return exact[0]

    starts = [w for w in candidates if normalize_title(w.title).startswith(search)]
    if starts:
        return starts[0]

    return candidates[0]


def get_window_hwnd(win):
    return getattr(win, '_hWnd', None) or getattr(win, 'hwnd', None)


def make_key_lparam(vk, keyup=False):
    scan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
    lparam = 1 | (scan << 16)
    if vk in EXTENDED_KEYS:
        lparam |= 0x01000000
    if keyup:
        lparam |= 0xC0000000
    return lparam


def set_foreground_window(hwnd):
    if not hwnd:
        return False
    try:
        fg = ctypes.windll.user32.GetForegroundWindow()
        if fg == hwnd:
            return True
        if ctypes.windll.user32.IsIconic(hwnd):
            ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)

        current_tid = ctypes.windll.kernel32.GetCurrentThreadId()
        fg_tid = ctypes.windll.user32.GetWindowThreadProcessId(fg, 0)
        target_tid = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, 0)
        ctypes.windll.user32.AttachThreadInput(current_tid, fg_tid, True)
        ctypes.windll.user32.AttachThreadInput(current_tid, target_tid, True)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
        ctypes.windll.user32.BringWindowToTop(hwnd)
        ctypes.windll.user32.SetActiveWindow(hwnd)
        ctypes.windll.user32.AttachThreadInput(current_tid, fg_tid, False)
        ctypes.windll.user32.AttachThreadInput(current_tid, target_tid, False)
        return True
    except Exception:
        return False


def activate_window(win):
    try:
        if hasattr(win, 'isMinimized') and win.isMinimized:
            win.restore()
    except Exception:
        pass
    try:
        win.activate()
    except Exception:
        pass

    hwnd = get_window_hwnd(win)
    if hwnd is not None:
        set_foreground_window(hwnd)

    time.sleep(0.25)


def key_to_vk(key):
    if not key:
        return None
    k = key.lower()
    if k in VK_MAPPING:
        return VK_MAPPING[k]
    if len(key) == 1:
        vk = ctypes.windll.user32.VkKeyScanW(ord(key)) & 0xFF
        if vk != 0xFF:
            return vk
        return ord(key.upper())
    return None


def parse_key_sequence(key_sequence):
    if not key_sequence:
        return []
    parts = [p.strip().lower() for p in key_sequence.replace(',', '+').split('+') if p.strip()]
    vks = []
    for part in parts:
        vk = VK_MAPPING.get(part)
        if vk is None:
            if len(part) == 1:
                vk = ctypes.windll.user32.VkKeyScanW(ord(part)) & 0xFF
                if vk == 0xFF:
                    vk = None
            elif part.startswith('f') and part[1:].isdigit():
                num = int(part[1:])
                if 1 <= num <= 24:
                    vk = 0x6F + num
            else:
                vk = None
        if vk is None:
            raise ValueError(f'Unknown key token: {part}')
        vks.append(vk)
    return vks


def press_keydown(hwnd, vk):
    if not hwnd or vk is None:
        return False
    return bool(ctypes.windll.user32.PostMessageW(hwnd, WM_KEYDOWN, vk, make_key_lparam(vk, keyup=False)))


def press_keyup(hwnd, vk):
    if not hwnd or vk is None:
        return False
    return bool(ctypes.windll.user32.PostMessageW(hwnd, WM_KEYUP, vk, make_key_lparam(vk, keyup=True)))


def send_key_sequence(hwnd, key_sequence):
    try:
        vks = parse_key_sequence(key_sequence)
    except ValueError:
        return False
    if not vks:
        return False
    for vk in vks:
        if not press_keydown(hwnd, vk):
            return False
        time.sleep(0.02)
    for vk in reversed(vks):
        if not press_keyup(hwnd, vk):
            return False
        time.sleep(0.02)
    return True


def post_key(hwnd, vk):
    if not hwnd or vk is None:
        return False
    res_down = press_keydown(hwnd, vk)
    time.sleep(0.03)
    res_up = press_keyup(hwnd, vk)
    time.sleep(0.03)
    return res_down and res_up


def post_text(hwnd, text):
    if not hwnd or not text:
        return False
    for ch in text:
        vk = key_to_vk(ch)
        if vk is None or vk == 0:
            vk = ctypes.windll.user32.VkKeyScanW(ord(ch)) & 0xFF
        if vk is None or vk == 0xFF:
            return False
        if not post_key(hwnd, vk):
            return False
    return True


KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ('wVk', ctypes.c_ushort),
        ('wScan', ctypes.c_ushort),
        ('dwFlags', ctypes.c_ulong),
        ('time', ctypes.c_ulong),
        ('dwExtraInfo', ctypes.c_void_p),
    ]


class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [('ki', KEYBDINPUT)]
    _anonymous_ = ('_input',)
    _fields_ = [('type', ctypes.c_ulong), ('_input', _INPUT)]


def send_system_key(vk, keyup=False):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = vk
    inp.ki.wScan = 0
    inp.ki.dwFlags = KEYEVENTF_KEYUP if keyup else 0
    inp.ki.time = 0
    inp.ki.dwExtraInfo = ctypes.cast(ctypes.pointer(ctypes.c_ulong(0)), ctypes.c_void_p)
    return ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp)) == 1


def send_system_text(text):
    for ch in text:
        vk = key_to_vk(ch)
        if vk is None or vk == 0:
            vk = ctypes.windll.user32.VkKeyScanW(ord(ch)) & 0xFF
        if vk is None or vk == 0xFF:
            return False
        if not send_system_key(vk, keyup=False):
            return False
        time.sleep(0.01)
        if not send_system_key(vk, keyup=True):
            return False
        time.sleep(0.01)
    return True


def paste_text_via_clipboard(hwnd, text):
    if not text or not hwnd:
        return False
    try:
        old_clip = pyperclip.paste()
    except Exception:
        old_clip = None

    try:
        pyperclip.copy(text)
    except Exception:
        return False

    try:
        ctypes.windll.user32.SendMessageW(hwnd, WM_PASTE, 0, 0)
    except Exception:
        pass

    success = send_system_key_sequence('ctrl+v')
    time.sleep(0.05)
    if old_clip is not None:
        try:
            pyperclip.copy(old_clip)
        except Exception:
            pass
    return success


def send_system_key_sequence(key_sequence):
    try:
        vks = parse_key_sequence(key_sequence)
    except ValueError:
        return False
    if not vks:
        return False
    for vk in vks:
        if not send_system_key(vk, keyup=False):
            return False
        time.sleep(0.02)
    for vk in reversed(vks):
        if not send_system_key(vk, keyup=True):
            return False
        time.sleep(0.02)
    return True


def send_console_command_via_window(win, command_text, console_key='`'):
    hwnd = get_window_hwnd(win)
    if hwnd is None:
        raise RuntimeError('Window handle not available for target window')

    try:
        if console_key:
            if not send_key_sequence(hwnd, console_key):
                raise RuntimeError(f'Failed to send console key sequence: {console_key!r}')
    except ValueError as e:
        raise RuntimeError(str(e)) from e

    time.sleep(0.20)
    if paste_text_via_clipboard(hwnd, command_text):
        return post_key(hwnd, key_to_vk('enter'))

    if post_text(hwnd, command_text) and post_key(hwnd, key_to_vk('enter')):
        return True

    # Fallback to foreground + system input if window messages don't work.
    activate_window(win)
    if console_key and not send_system_key_sequence(console_key):
        raise RuntimeError(f'Failed to send console key via system input: {console_key!r}')
    if not send_system_text(command_text + '\r'):
        raise RuntimeError('Both window-post and system input methods failed')

    return True


def send_listplayers_to_game(window_title, console_key='`'):
    if not check_deps():
        return None
    win = find_window(window_title)
    if not win:
        messagebox.showerror("Window not found", f"Could not find a window with title containing '{window_title}'")
        return None

    activate_window(win)

    try:
        if not send_console_command_via_window(win, 'listplayers', console_key):
            raise RuntimeError('Failed to send command to window')
    except Exception as e:
        messagebox.showerror("Input error", f"Failed to send keys: {e}")
        return None

    # wait a bit for the game to process and copy results to clipboard
    timeout = 6.0
    poll = 0.2
    waited = 0.0
    last_clip = ''
    while waited < timeout:
        time.sleep(poll)
        waited += poll
        try:
            clip = pyperclip.paste()
        except Exception:
            clip = ''
        if clip and clip != last_clip:
            return clip
        last_clip = clip

    # final attempt
    try:
        return pyperclip.paste()
    except Exception:
        return None


def send_command_to_game(window_title, command_text, console_key='`'):
    """Focus the game window and send a single console command (no clipboard wait)."""
    if not check_deps():
        return False
    win = find_window(window_title)
    if not win:
        messagebox.showerror("Window not found", f"Could not find a window with title containing '{window_title}'")
        return False

    activate_window(win)

    try:
        return send_console_command_via_window(win, command_text, console_key)
    except Exception as e:
        messagebox.showerror("Input error", f"Failed to send keys: {e}")
        return False


def parse_players(text):
    if not text:
        return []
    players = []
    lines = text.splitlines()
    # pattern for explicit PlayFab id fields
    playfab_re = re.compile(r'^[A-Fa-f0-9]{8,}$')
    # legacy fallback patterns
    id_re = re.compile(r'PlayFabId[:\s]*([A-Za-z0-9\-_:]+)', re.IGNORECASE)
    fallback_id_re = re.compile(r'([A-Za-z0-9\-]{8,})')

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        # skip header lines
        low = line.lower()
        if low.startswith('servername') or low.startswith('name -') or 'playfabplayerid' in low:
            continue

        # structured format: fields separated by ' - '
        if ' - ' in line:
            parts = [p.strip() for p in line.split(' - ')]
            if len(parts) >= 2:
                name = parts[0] or '<unknown>'
                playfab = parts[1]
                ping = ''
                if len(parts) >= 6:
                    ping = parts[-1]
                    # normalize ping: remove 'ms' and whitespace
                    ping = ping.replace('ms', '').strip()
                if playfab and playfab_re.fullmatch(playfab):
                    players.append((name, playfab, ping))
                    continue

        # fallback: find explicit PlayFabId: pattern or generic id-like token
        m = id_re.search(line)
        if m:
            pid = m.group(1)
            # name is text before the id if possible
            name = line[:m.start()].strip().strip(' -:()') or '<unknown>'
            players.append((name, pid, ''))
            continue

        fm = fallback_id_re.search(line)
        if fm:
            pid = fm.group(1)
            # validate fallback token looks like an id (has digits or is hex-like)
            if not (re.search(r'\d', pid) or playfab_re.fullmatch(pid)):
                # ignore tokens that are likely command words (e.g. 'Serversay')
                continue
            name = line.replace(pid, '').strip(' -:()') or '<unknown>'
            players.append((name, pid, ''))

    # dedupe preserving order
    seen = set()
    out = []
    for row in players:
        # row may be (name,id) or (name,id,ping)
        if len(row) == 2:
            n, i = row
            p = ''
        else:
            n, i, p = row
        key = (n, i)
        if key in seen:
            continue
        seen.add(key)
        out.append((n, i, p))
    return out


class App:
    def __init__(self, root):
        self.root = root
        root.title('Chivalry 2 Admin Tool')

        frm = tk.Frame(root)
        frm.pack(padx=8, pady=8)

        tk.Label(frm, text='Game window title substring:').grid(row=0, column=0, sticky='w')
        self.win_entry = tk.Entry(frm, width=30)
        self.win_entry.grid(row=0, column=1, sticky='w')
        self.win_entry.insert(0, 'Chivalry 2')

        tk.Label(frm, text='Console toggle key:').grid(row=1, column=0, sticky='w')
        self.key_entry = tk.Entry(frm, width=10)
        self.key_entry.grid(row=1, column=1, sticky='w')
        self.key_entry.insert(0, '`')

        btn = tk.Button(frm, text="Run 'listplayers'", command=self.on_run)
        btn.grid(row=2, column=0, columnspan=2, pady=(6, 6))

        self.status = tk.Label(frm, text='Ready', anchor='w')
        self.status.grid(row=3, column=0, columnspan=2, sticky='we')

        self.tree = ttk.Treeview(root, columns=('name', 'id', 'ping'), show='headings', height=15)
        self.tree.heading('name', text='Name')
        self.tree.heading('id', text='PlayFabId')
        self.tree.heading('ping', text='Ping (ms)')
        self.tree.column('name', width=300)
        self.tree.column('id', width=220)
        self.tree.column('ping', width=80, anchor='center')
        self.tree.pack(padx=8, pady=(0, 8))
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        self.tree.bind('<Double-1>', self.on_double_click)

        btnfrm = tk.Frame(root)
        btnfrm.pack(padx=8, pady=(0,8))
        tk.Button(btnfrm, text='Copy selected PlayFabId', command=self.copy_selected).pack(side='left')
        tk.Button(btnfrm, text='Paste from clipboard', command=self.paste_clipboard).pack(side='left', padx=(6,0))

        # search controls
        searchfrm = tk.Frame(root)
        searchfrm.pack(fill='x', padx=8, pady=(6,0))
        tk.Label(searchfrm, text='Search username:').pack(side='left')
        self.search_entry = tk.Entry(searchfrm, width=30)
        self.search_entry.pack(side='left', padx=(6,6))
        self.search_entry.bind('<Return>', self.on_search)
        tk.Button(searchfrm, text='Search', command=self.on_search).pack(side='left')
        tk.Button(searchfrm, text='Clear', command=self.clear_search).pack(side='left', padx=(6,0))

        self.all_players = []

        # admin commands frame
        cmdfrm = tk.LabelFrame(root, text='Admin Commands')
        cmdfrm.pack(fill='x', padx=8, pady=(6,8))

        # ID and duration inputs
        idfrm = tk.Frame(cmdfrm)
        idfrm.pack(fill='x', padx=6, pady=(6,0))
        tk.Label(idfrm, text='PlayFabId:').pack(side='left')
        self.id_entry = tk.Entry(idfrm, width=28)
        self.id_entry.pack(side='left', padx=(6,12))
        tk.Label(idfrm, text='Duration (hours):').pack(side='left')
        self.duration_entry = tk.Entry(idfrm, width=6)
        self.duration_entry.pack(side='left', padx=(6,0))

        reasonfrm = tk.Frame(cmdfrm)
        reasonfrm.pack(fill='x', padx=6, pady=(4,0))
        tk.Label(reasonfrm, text='Ban/Kick reason (optional):').pack(side='left')
        self.reason_entry = tk.Entry(reasonfrm, width=44)
        self.reason_entry.pack(side='left', padx=(6,0))

        btn2frm = tk.Frame(cmdfrm)
        btn2frm.pack(fill='x', padx=6, pady=(6,8))
        tk.Button(btn2frm, text='Kick by ID', command=self.kick_by_id).pack(side='left')
        tk.Button(btn2frm, text='Ban by ID', command=self.ban_by_id).pack(side='left', padx=(6,0))
        tk.Button(btn2frm, text='Unban by ID', command=self.unban_by_id).pack(side='left', padx=(6,0))

        # ping kick
        pingfrm = tk.Frame(cmdfrm)
        pingfrm.pack(fill='x', padx=6, pady=(0,6))
        tk.Label(pingfrm, text='Kick players above ping (min 100 ms):').pack(side='left')
        self.ping_entry = tk.Entry(pingfrm, width=6)
        self.ping_entry.pack(side='left', padx=(6,6))
        self.ping_entry.insert(0, '100')
        tk.Button(pingfrm, text='Kick high ping', command=self.kick_high_ping).pack(side='left')

        # serversay
        sayfrm = tk.Frame(cmdfrm)
        sayfrm.pack(fill='x', padx=6, pady=(0,6))
        tk.Label(sayfrm, text='Server message:').pack(side='left')
        self.msg_entry = tk.Entry(sayfrm, width=60)
        self.msg_entry.pack(side='left', padx=(6,6))
        tk.Button(sayfrm, text='Send', command=self.serversay).pack(side='left')

        # start game button
        startfrm = tk.Frame(cmdfrm)
        startfrm.pack(fill='x', padx=6, pady=(0,6))
        tk.Button(startfrm, text='Start Game Now (TBSmanuallystartgame)', command=self.start_game).pack(side='left')

    def set_status(self, text):
        self.status.config(text=text)

    def on_run(self):
        if not check_deps():
            return
        self.set_status('Sending command to game...')
        t = threading.Thread(target=self._run_thread, daemon=True)
        t.start()

    def _run_thread(self):
        title = self.win_entry.get().strip()
        key = self.key_entry.get().strip() or '`'
        clip = send_listplayers_to_game(title, key)
        if not clip:
            self.set_status('No clipboard output received.')
            return
        self.set_status('Parsing clipboard...')
        players = parse_players(clip)
        self.root.after(0, lambda: self.populate(players))

    def _run_command_thread(self, command_text):
        title = self.win_entry.get().strip()
        self.set_status(f"Sending: {command_text}")
        ok = send_command_to_game(title, command_text, self.key_entry.get().strip() or '`')
        if ok:
            self.set_status('Command sent')
        else:
            self.set_status('Command failed')

    def kick_by_id(self):
        pid = (self.id_entry.get() or '').strip()
        reason = (self.reason_entry.get() or '').strip()
        if not pid:
            messagebox.showerror('Missing id', 'Please enter a PlayFabId to kick')
            return
        if reason:
            reason = reason.replace('"', "'")
            cmd = f'kickbyid {pid} "{reason}"'
        else:
            cmd = f'kickbyid {pid}'
        threading.Thread(target=self._run_command_thread, args=(cmd,), daemon=True).start()

    def ban_by_id(self):
        pid = (self.id_entry.get() or '').strip()
        dur = (self.duration_entry.get() or '').strip()
        reason = (self.reason_entry.get() or '').strip()
        if not pid or not dur:
            messagebox.showerror('Missing fields', 'Please enter PlayFabId and duration (hours)')
            return
        # ensure numeric hours
        try:
            hours = int(dur)
        except ValueError:
            messagebox.showerror('Invalid duration', 'Duration must be an integer number of hours')
            return
        if reason:
            reason = reason.replace('"', "'")
            cmd = f'banbyid {pid} {hours} "{reason}"'
        else:
            cmd = f'banbyid {pid} {hours}'
        threading.Thread(target=self._run_command_thread, args=(cmd,), daemon=True).start()

    def kick_high_ping(self):
        raw = (self.ping_entry.get() or '').strip()
        if not raw:
            messagebox.showerror('Missing ping', 'Please enter a ping threshold in milliseconds')
            return
        try:
            threshold = int(raw)
        except ValueError:
            messagebox.showerror('Invalid ping', 'Ping threshold must be an integer number of milliseconds')
            return
        if threshold < 100:
            messagebox.showerror('Invalid ping', 'Minimum threshold is 100 ms')
            return
        if not self.all_players:
            messagebox.showerror('No players loaded', 'Please run listplayers first to load player ping values')
            return

        candidates = []
        for name, pid, ping in self.all_players:
            try:
                value = int(str(ping).strip())
            except (ValueError, TypeError):
                continue
            if value > threshold:
                candidates.append((name, pid, value))

        if not candidates:
            self.set_status(f'No players above {threshold} ms')
            return

        threading.Thread(target=self._run_kick_high_ping_thread, args=(threshold, candidates), daemon=True).start()

    def _run_kick_high_ping_thread(self, threshold, candidates):
        title = self.win_entry.get().strip()
        key = self.key_entry.get().strip() or '`'
        sent = 0
        failed = 0
        for name, pid, ping in candidates:
            self.root.after(0, lambda name=name, ping=ping: self.set_status(f'Kicking {name} ({ping} ms)'))
            ok = send_command_to_game(title, f'kickbyid {pid}', key)
            if ok:
                sent += 1
            else:
                failed += 1
            time.sleep(0.25)
        self.root.after(0, lambda: self.set_status(f'Kicked {sent} players above {threshold} ms; failed {failed}'))

    def unban_by_id(self):
        pid = (self.id_entry.get() or '').strip()
        if not pid:
            messagebox.showerror('Missing id', 'Please enter a PlayFabId to unban')
            return
        cmd = f'unbanbyid {pid}'
        threading.Thread(target=self._run_command_thread, args=(cmd,), daemon=True).start()

    def serversay(self):
        msg = (self.msg_entry.get() or '').strip()
        if not msg:
            messagebox.showerror('Missing message', 'Please enter a message to send')
            return
        # quote message if needed
        cmd = f'Serversay {msg}'
        threading.Thread(target=self._run_command_thread, args=(cmd,), daemon=True).start()

    def start_game(self):
        cmd = 'TBSmanuallystartgame'
        threading.Thread(target=self._run_command_thread, args=(cmd,), daemon=True).start()

    def populate(self, players, set_all=True):
        if set_all:
            self.all_players = players
        for i in self.tree.get_children():
            self.tree.delete(i)
        if not players:
            self.set_status('No players parsed from clipboard.')
            return
        for name, pid, ping in players:
            self.tree.insert('', tk.END, values=(name, pid, ping))
        self.set_status(f'Parsed {len(players)} players.')

    def on_search(self, event=None):
        q = (self.search_entry.get() or '').strip()
        if not q:
            self.populate(self.all_players, set_all=False)
            return
        qf = q.casefold()
        filtered = [p for p in self.all_players if qf in (p[0] or '').casefold()]
        self.populate(filtered, set_all=False)

    def clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.populate(self.all_players, set_all=False)

    def copy_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        vals = item.get('values', [])
        if len(vals) >= 2:
            pid = vals[1]
        else:
            pid = ''
        try:
            pyperclip.copy(pid)
            self.set_status('PlayFabId copied to clipboard.')
        except Exception as e:
            messagebox.showerror('Clipboard error', str(e))

    def on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        vals = item.get('values', [])
        if not vals:
            return
        name = vals[0] if len(vals) > 0 else ''
        pid = vals[1] if len(vals) > 1 else ''
        ping = vals[2] if len(vals) > 2 else ''
        try:
            # populate the id entry for quick actions
            self.id_entry.delete(0, tk.END)
            self.id_entry.insert(0, pid)
        except Exception:
            pass
        self.set_status(f"Selected: {name} (ping: {ping} ms)")

    def on_double_click(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        vals = item.get('values', [])
        if len(vals) >= 2:
            pid = vals[1]
            try:
                pyperclip.copy(pid)
                self.set_status('PlayFabId copied to clipboard.')
            except Exception as e:
                messagebox.showerror('Clipboard error', str(e))

    def paste_clipboard(self):
        try:
            raw = pyperclip.paste()
        except Exception as e:
            messagebox.showerror('Clipboard error', str(e))
            return
        players = parse_players(raw)
        self.populate(players)


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
