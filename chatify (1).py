import tkinter as tk
from tkinter import messagebox
import json, os, threading, urllib.request, urllib.error
from datetime import datetime

# ── LUXURY DARK GLASS PALETTE ──────────────────────────────────────────
BG        = "#060709"
SIDEBAR   = "#090b12"
GLASS     = "#0d1018"
GLASS2    = "#111520"
GLASS3    = "#161b28"
GLASS_HVR = "#181e2e"
BORDER    = "#0e1e32"
BORDER_LT = "#162840"

CYAN      = "#00d4ff"
CYAN_DIM  = "#008aaa"
CYAN_DARK = "#002a3d"
CYAN_GLOW = "#00b8dd"
BLUE      = "#1a6aff"
GREEN     = "#00e5a0"
GREEN_DIM = "#009966"
AMBER     = "#ffb020"
RED       = "#ff3a5c"
PURPLE    = "#9b6dff"

TEXT      = "#eaf4ff"
TEXT2     = "#5a7a9a"
DIM       = "#3a5a7a"

FONT      = "Helvetica"
FONT_B    = "Helvetica"

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chatify_data.json")
CFG_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chatify_cfg.json")

API_URL   = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
MODEL     = "gemini-2.5-flash"


# ── HELPERS ────────────────────────────────────────────────────────────
def rrect(canvas, x1, y1, x2, y2, r, **kw):
    r = max(1, min(r, (x2-x1)//2, (y2-y1)//2))
    pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r,
           x2,y2-r, x2,y2, x2-r,y2, x1+r,y2,
           x1,y2, x1,y2-r, x1,y1+r, x1,y1, x1+r,y1]
    return canvas.create_polygon(pts, smooth=True, **kw)

def pill(canvas, x1, y1, x2, y2, **kw):
    """Full pill — radius = half height."""
    r = (y2 - y1) // 2
    return rrect(canvas, x1, y1, x2, y2, r, **kw)

def circle_canvas(parent, size, bg_outer, fill, text="", text_color=BG, font_size=10):
    c = tk.Canvas(parent, width=size, height=size, bg=bg_outer,
                  highlightthickness=0, bd=0)
    c.create_oval(1, 1, size-1, size-1, fill=fill, outline="")
    if text:
        c.create_text(size//2, size//2, text=text,
                      fill=text_color, font=(FONT, font_size, "bold"))
    return c


# ── GEMINI API ─────────────────────────────────────────────────────────
def call_gemini(api_key, messages):
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    payload = json.dumps({
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.7},
    }).encode("utf-8")
    url = f"{API_URL}?key={api_key}"
    req = urllib.request.Request(url, data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Chatify/1.0"},
        method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["candidates"][0]["content"]["parts"][0]["text"]


# ── APP ────────────────────────────────────────────────────────────────
class Chatify:
    def __init__(self, root):
        self.root      = root
        self.root.title("Chatify")
        self.root.geometry("960x720")
        self.root.minsize(720, 520)
        self.root.configure(bg=BG)

        self.api_key   = ""
        self.chats     = []
        self.active_id = None
        self._typing   = False

        self._load_cfg(); self._load_data()
        self._build_ui()

        if not self.api_key:
            self.root.after(300, self._ask_api_key)
        elif not self.chats:
            self._new_chat()
        else:
            self._open_chat(self.chats[0]["id"])

    # ── PERSISTENCE ───────────────────────────────────────────────────
    def _load_cfg(self):
        try:
            with open(CFG_FILE) as f: self.api_key = json.load(f).get("api_key","")
        except: self.api_key = ""

    def _save_cfg(self):
        with open(CFG_FILE,"w") as f: json.dump({"api_key": self.api_key}, f)

    def _load_data(self):
        try:
            with open(SAVE_FILE) as f: self.chats = json.load(f)
        except: self.chats = []

    def _save_data(self):
        with open(SAVE_FILE,"w") as f: json.dump(self.chats, f, indent=2)

    # ── UI ────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Thin cyan top bar
        tk.Frame(self.root, bg=CYAN, height=2).pack(fill="x")

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True)

        # ══ SIDEBAR ══════════════════════════════════════════
        self.sidebar = tk.Frame(main, bg=SIDEBAR, width=230)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Sidebar top — logo + gear
        top = tk.Frame(self.sidebar, bg=SIDEBAR)
        top.pack(fill="x", padx=18, pady=(22, 16))

        # Logo circle
        logo_c = circle_canvas(top, 34, SIDEBAR, CYAN, "C", BG, 12)
        logo_c.pack(side="left")
        name_f = tk.Frame(top, bg=SIDEBAR)
        name_f.pack(side="left", padx=(10,0))
        tk.Label(name_f, text="Chatify", font=(FONT, 13, "bold"),
                 bg=SIDEBAR, fg=TEXT).pack(anchor="w")
        tk.Label(name_f, text="AI Assistant", font=(FONT, 7),
                 bg=SIDEBAR, fg=TEXT2).pack(anchor="w")

        # Gear icon
        gear = tk.Label(top, text="⚙", font=(FONT, 13), bg=SIDEBAR,
                        fg=DIM, cursor="hand2")
        gear.pack(side="right")
        gear.bind("<Button-1>", lambda e: self._ask_api_key())
        gear.bind("<Enter>",    lambda e: gear.config(fg=CYAN))
        gear.bind("<Leave>",    lambda e: gear.config(fg=DIM))

        # New chat pill button
        nc_c = tk.Canvas(self.sidebar, height=40, bg=SIDEBAR,
                         highlightthickness=0, bd=0, cursor="hand2")
        nc_c.pack(fill="x", padx=18, pady=(0,16))
        nc_c.bind("<Configure>", lambda e: self._draw_nc_btn(nc_c, False))
        nc_c.bind("<Enter>",     lambda e: self._draw_nc_btn(nc_c, True))
        nc_c.bind("<Leave>",     lambda e: self._draw_nc_btn(nc_c, False))
        nc_c.bind("<ButtonRelease-1>", lambda e: self._new_chat())
        self._nc_canvas = nc_c

        # Divider
        tk.Frame(self.sidebar, bg=BORDER_LT, height=1).pack(fill="x", padx=18, pady=(0,10))

        # Chat list
        self.chat_list_frame = tk.Frame(self.sidebar, bg=SIDEBAR)
        self.chat_list_frame.pack(fill="both", expand=True, padx=10)

        # Model pill at bottom
        tk.Frame(self.sidebar, bg=BORDER, height=1).pack(fill="x", padx=18, pady=(8,0))
        model_lbl = tk.Label(self.sidebar, text=f"✦  {MODEL}",
                             font=(FONT, 7), bg=SIDEBAR, fg=DIM)
        model_lbl.pack(pady=(8,14))

        # ══ CHAT AREA ════════════════════════════════════════
        chat_area = tk.Frame(main, bg=BG)
        chat_area.pack(side="left", fill="both", expand=True)

        # Chat header bar
        self.chat_hdr = tk.Frame(chat_area, bg=GLASS, height=58)
        self.chat_hdr.pack(fill="x")
        self.chat_hdr.pack_propagate(False)

        # AI avatar in header
        self._hdr_av = circle_canvas(self.chat_hdr, 34, GLASS, CYAN_DARK, "✦", CYAN, 10)
        self._hdr_av.pack(side="left", padx=(18,10), pady=12)

        hdr_txt = tk.Frame(self.chat_hdr, bg=GLASS)
        hdr_txt.pack(side="left", pady=14)
        self.chat_title = tk.Label(hdr_txt, text="", font=(FONT, 11, "bold"),
                                    bg=GLASS, fg=TEXT)
        self.chat_title.pack(anchor="w")
        self.chat_sub = tk.Label(hdr_txt, text="", font=(FONT, 7),
                                  bg=GLASS, fg=TEXT2)
        self.chat_sub.pack(anchor="w")

        # Online dot
        od = tk.Canvas(self.chat_hdr, width=8, height=8, bg=GLASS,
                       highlightthickness=0)
        od.pack(side="left", padx=(8,0), pady=14)
        od.create_oval(0, 0, 8, 8, fill=GREEN, outline="")

        # Delete button
        del_c = tk.Canvas(self.chat_hdr, width=32, height=32, bg=GLASS,
                          highlightthickness=0, cursor="hand2")
        del_c.pack(side="right", padx=18, pady=13)
        del_c.bind("<Configure>", lambda e: self._draw_del_btn(del_c, False))
        del_c.bind("<Enter>",     lambda e: self._draw_del_btn(del_c, True))
        del_c.bind("<Leave>",     lambda e: self._draw_del_btn(del_c, False))
        del_c.bind("<ButtonRelease-1>", lambda e: self._delete_chat())
        self._del_canvas = del_c

        # Thin glow border under header
        glow = tk.Canvas(chat_area, height=2, bg=BG, highlightthickness=0)
        glow.pack(fill="x")
        glow.bind("<Configure>", lambda e: (
            glow.delete("all"),
            glow.create_line(0, 1, e.width, 1, fill=BORDER_LT, width=1)
        ))

        # Messages area
        msg_wrap = tk.Frame(chat_area, bg=BG)
        msg_wrap.pack(fill="both", expand=True)
        self.msg_canvas = tk.Canvas(msg_wrap, bg=BG, bd=0,
                                     highlightthickness=0, yscrollincrement=2)
        msg_sb = tk.Scrollbar(msg_wrap, orient="vertical",
                               command=self.msg_canvas.yview)
        self.msg_canvas.configure(yscrollcommand=msg_sb.set)
        msg_sb.pack(side="right", fill="y")
        self.msg_canvas.pack(side="left", fill="both", expand=True)
        self.msg_inner = tk.Frame(self.msg_canvas, bg=BG)
        self.msg_win   = self.msg_canvas.create_window((0,0),
                          window=self.msg_inner, anchor="nw")
        self.msg_inner.bind("<Configure>",
            lambda e: self.msg_canvas.configure(
                scrollregion=self.msg_canvas.bbox("all")))
        self.msg_canvas.bind("<Configure>",
            lambda e: self.msg_canvas.itemconfig(self.msg_win, width=e.width))
        self.msg_canvas.bind_all("<MouseWheel>",
            lambda e: self.msg_canvas.yview_scroll(-1*(e.delta//120), "units"))

        # ── Input bar ─────────────────────────────────────────
        inp_outer = tk.Frame(chat_area, bg=BG)
        inp_outer.pack(fill="x", padx=20, pady=(10, 16))

        # Pill-shaped input container
        self._inp_wrap_c = tk.Canvas(inp_outer, height=52, bg=BG,
                                      highlightthickness=0, bd=0)
        self._inp_wrap_c.pack(fill="x", side="left", expand=True)
        self._inp_wrap_f = tk.Frame(self._inp_wrap_c, bg=GLASS2)
        self._inp_wrap_c.bind("<Configure>", self._draw_input_bg)

        self.inp = tk.Text(self._inp_wrap_f, height=1, bg=GLASS2, fg=TEXT,
                           insertbackground=CYAN, font=(FONT, 11),
                           bd=0, highlightthickness=0, relief="flat", wrap="word")
        self.inp.pack(fill="x", padx=18, pady=14)
        self.inp.bind("<Return>",       self._on_enter)
        self.inp.bind("<Shift-Return>", lambda e: None)
        self.inp.bind("<FocusIn>",  lambda e: self._draw_input_bg(focused=True))
        self.inp.bind("<FocusOut>", lambda e: self._draw_input_bg(focused=False))
        self._inp_focused = False

        # Send circle button
        send_c = tk.Canvas(inp_outer, width=52, height=52, bg=BG,
                           highlightthickness=0, bd=0, cursor="hand2")
        send_c.pack(side="right", padx=(10,0))
        send_c.bind("<Configure>",       lambda e: self._draw_send(send_c, False))
        send_c.bind("<Enter>",           lambda e: self._draw_send(send_c, True))
        send_c.bind("<Leave>",           lambda e: self._draw_send(send_c, False))
        send_c.bind("<ButtonRelease-1>", lambda e: self._send())
        self._send_c = send_c

        tk.Frame(self.root, bg=CYAN_DIM, height=1).pack(fill="x", side="bottom")
        self._refresh_sidebar()

    def _draw_nc_btn(self, c, hot):
        c.delete("all")
        w = c.winfo_width() or 194
        h = c.winfo_height() or 40
        fill = CYAN_GLOW if hot else CYAN
        pill(c, 0, 0, w, h, fill=fill, outline="")
        c.create_text(w//2, h//2, text="＋  New Chat",
                      fill=BG, font=(FONT, 10, "bold"))

    def _draw_send(self, c, hot):
        c.delete("all")
        w = c.winfo_width() or 52
        h = c.winfo_height() or 52
        fill = CYAN_GLOW if hot else CYAN
        c.create_oval(1, 1, w-1, h-1, fill=fill, outline="")
        c.create_text(w//2, h//2+1, text="↑", fill=BG, font=(FONT, 16, "bold"))

    def _draw_del_btn(self, c, hot):
        c.delete("all")
        w = c.winfo_width() or 32
        h = c.winfo_height() or 32
        fill = "#2a0a10" if hot else GLASS
        c.create_oval(1, 1, w-1, h-1, fill=fill, outline=RED if hot else BORDER_LT)
        c.create_text(w//2, h//2, text="✕", fill=RED if hot else DIM,
                      font=(FONT, 10))

    def _draw_input_bg(self, e=None, focused=False):
        c = self._inp_wrap_c
        c.delete("all")
        w = c.winfo_width() or 600
        h = c.winfo_height() or 52
        border = CYAN_DIM if focused or self._inp_focused else BORDER_LT
        rrect(c, 0, 0, w, h, h//2, fill=border, outline="")
        rrect(c, 1, 1, w-1, h-1, h//2-1, fill=GLASS2, outline="")
        self._inp_wrap_f.place(x=0, y=0, width=w, height=h)

    # ── SIDEBAR ───────────────────────────────────────────────────────
    def _refresh_sidebar(self):
        for w in self.chat_list_frame.winfo_children(): w.destroy()
        for chat in reversed(self.chats):
            self._sidebar_item(chat)

    def _sidebar_item(self, chat):
        is_active = chat["id"] == self.active_id
        bg_n = GLASS3 if is_active else SIDEBAR
        bg_h = GLASS_HVR

        # Pill container
        pill_c = tk.Canvas(self.chat_list_frame, height=58, bg=SIDEBAR,
                           highlightthickness=0, bd=0, cursor="hand2")
        pill_c.pack(fill="x", pady=3)
        pill_c.bind("<Configure>",
                    lambda e, c=pill_c, a=is_active: self._draw_sb_item(c, a, False))

        inner = tk.Frame(pill_c, bg=bg_n, cursor="hand2")
        pill_c.create_window(0, 0, window=inner, anchor="nw")

        # Small colored dot or active indicator
        dot_color = CYAN if is_active else DIM
        dot_c = tk.Canvas(inner, width=8, height=8, bg=bg_n, highlightthickness=0)
        dot_c.pack(side="left", padx=(12,8), pady=25)
        dot_c.create_oval(0, 0, 8, 8, fill=dot_color, outline="")

        txt_f = tk.Frame(inner, bg=bg_n, cursor="hand2")
        txt_f.pack(side="left", fill="x", expand=True, pady=10)
        title = chat["title"][:24] + "…" if len(chat["title"]) > 24 else chat["title"]
        tk.Label(txt_f, text=title,
                 font=(FONT, 10, "bold" if is_active else "normal"),
                 bg=bg_n, fg=CYAN if is_active else TEXT,
                 anchor="w").pack(anchor="w")
        count = len(chat["messages"])
        tk.Label(txt_f, text=f"{count} message{'s' if count!=1 else ''}",
                 font=(FONT, 7), bg=bg_n,
                 fg=TEXT2 if is_active else DIM, anchor="w").pack(anchor="w")

        def click(e, cid=chat["id"]): self._open_chat(cid)
        def enter(e, c=pill_c, a=is_active): self._draw_sb_item(c, a, True)
        def leave(e, c=pill_c, a=is_active): self._draw_sb_item(c, a, False)

        for w in [pill_c, inner, txt_f, dot_c] + list(txt_f.winfo_children()):
            w.bind("<Button-1>", click)
            if not is_active:
                w.bind("<Enter>", enter)
                w.bind("<Leave>", leave)

        pill_c.bind("<Configure>",
                    lambda e, c=pill_c, i=inner, a=is_active:
                    (self._draw_sb_item(c, a, False),
                     i.place(x=0, y=0, width=e.width, height=e.height)))

    def _draw_sb_item(self, c, active, hover):
        c.delete("bg")
        w = c.winfo_width() or 210
        h = c.winfo_height() or 58
        if active:
            rrect(c, 0, 0, w, h, 12, fill=GLASS3,   outline="", tags="bg")
            rrect(c, 1, 1, w-1, h-1, 11, fill=GLASS3, outline="", tags="bg")
        elif hover:
            rrect(c, 0, 0, w, h, 12, fill=BORDER,     outline="", tags="bg")
            rrect(c, 1, 1, w-1, h-1, 11, fill=GLASS,  outline="", tags="bg")

    # ── CHAT MANAGEMENT ───────────────────────────────────────────────
    def _new_chat(self):
        cid  = datetime.now().strftime("%Y%m%d%H%M%S%f")
        chat = {"id": cid, "title": "New Chat", "messages": []}
        self.chats.append(chat)
        self._save_data()
        self._open_chat(cid)

    def _open_chat(self, cid):
        self.active_id = cid
        chat = self._get_chat(cid)
        if not chat: return
        self.chat_title.config(text=chat["title"])
        count = len(chat["messages"])
        self.chat_sub.config(text=f"{count} message{'s' if count!=1 else ''}")
        self._refresh_sidebar()
        self._render_messages()

    def _get_chat(self, cid):
        return next((c for c in self.chats if c["id"]==cid), None)

    def _delete_chat(self):
        if not self.active_id: return
        if not messagebox.askyesno("Delete", "Delete this conversation?"): return
        self.chats     = [c for c in self.chats if c["id"] != self.active_id]
        self.active_id = None
        self._save_data(); self._refresh_sidebar()
        self._clear_messages()
        self.chat_title.config(text=""); self.chat_sub.config(text="")
        if self.chats: self._open_chat(self.chats[-1]["id"])
        else:          self._new_chat()

    # ── MESSAGES ──────────────────────────────────────────────────────
    def _clear_messages(self):
        for w in self.msg_inner.winfo_children(): w.destroy()

    def _render_messages(self):
        self._clear_messages()
        self.msg_inner.update_idletasks()
        chat = self._get_chat(self.active_id)
        if not chat: return
        if not chat["messages"]:
            self._show_empty(); return
        for msg in chat["messages"]:
            self._bubble(msg["role"], msg["content"], msg.get("time",""))
        self.msg_inner.update_idletasks()
        self.msg_canvas.configure(scrollregion=self.msg_canvas.bbox("all"))
        self.root.after(150, self._scroll_bottom)

    def _show_empty(self):
        tk.Frame(self.msg_inner, bg=BG, height=160).pack(fill="x")
        wrap = tk.Frame(self.msg_inner, bg=BG)
        wrap.pack(fill="x")

        # Big glowing circle
        av = tk.Canvas(wrap, width=70, height=70, bg=BG, highlightthickness=0)
        av.pack()
        av.create_oval(4, 4, 66, 66, fill=CYAN_DARK, outline=CYAN_DIM, width=1)
        av.create_text(35, 35, text="✦", fill=CYAN, font=(FONT, 22))

        tk.Label(wrap, text="Start a conversation",
                 font=(FONT, 15, "bold"), bg=BG, fg=TEXT).pack(pady=(14,4))
        tk.Label(wrap, text="Ask me anything  ·  Powered by Gemini",
                 font=(FONT, 9), bg=BG, fg=TEXT2).pack()

        # Suggestion pills
        sug_f = tk.Frame(wrap, bg=BG)
        sug_f.pack(pady=(20,0))
        for s in ["Say hello 👋", "Tell me a joke", "What can you do?"]:
            self._suggestion_pill(sug_f, s)

    def _suggestion_pill(self, parent, text):
        c = tk.Canvas(parent, height=32, bg=BG, highlightthickness=0, cursor="hand2")
        c.pack(side="left", padx=4)
        # measure text width
        tmp = tk.Label(text=text, font=(FONT, 9))
        tmp.update_idletasks()
        tw = tmp.winfo_reqwidth() + 24
        tmp.destroy()
        c.config(width=tw)
        c.create_rectangle(0, 0, tw, 32, fill=BG, outline="")  # placeholder
        c.bind("<Configure>", lambda e, c=c, t=text, w=tw: (
            c.delete("all"),
            rrect(c, 0, 0, w, 32, 16, fill=GLASS3, outline=""),
            c.create_text(w//2, 16, text=t, fill=TEXT2, font=(FONT, 9))
        ))
        c.bind("<Enter>", lambda e, c=c, t=text, w=tw: (
            c.delete("all"),
            rrect(c, 0, 0, w, 32, 16, fill=GLASS, outline=""),
            c.create_text(w//2, 16, text=t, fill=CYAN, font=(FONT, 9))
        ))
        c.bind("<Leave>", lambda e, c=c, t=text, w=tw: (
            c.delete("all"),
            rrect(c, 0, 0, w, 32, 16, fill=GLASS3, outline=""),
            c.create_text(w//2, 16, text=t, fill=TEXT2, font=(FONT, 9))
        ))
        c.bind("<ButtonRelease-1>", lambda e, t=text: self._send_text(t))

    def _bubble(self, role, content, time_str=""):
        is_user = role == "user"
        wrap = tk.Frame(self.msg_inner, bg=BG)
        wrap.pack(fill="x", padx=16, pady=5)

        if is_user:
            # ── User bubble — right, cyan pill ──
            outer = tk.Frame(wrap, bg=BG)
            outer.pack(side="right")

            # Pill bubble via canvas
            lines  = content.count("\n") + 1
            chars  = max(len(l) for l in content.split("\n")) if content else 1
            bw     = min(max(chars * 7 + 40, 80), 480)
            bh     = lines * 22 + 24

            bc = tk.Canvas(outer, width=bw, height=bh, bg=BG,
                           highlightthickness=0)
            bc.pack()
            rrect(bc, 0, 0, bw, bh, 18, fill=CYAN_DARK, outline="")
            bc.create_text(bw//2, bh//2, text=content,
                           fill=TEXT, font=(FONT, 11),
                           width=bw-28, justify="left")

            if time_str:
                tk.Label(outer, text=time_str, font=(FONT, 7),
                         bg=BG, fg=DIM).pack(anchor="e", pady=(2,0))

        else:
            # ── AI bubble — left, glass pill ──
            outer = tk.Frame(wrap, bg=BG)
            outer.pack(side="left", fill="x", expand=True)

            row = tk.Frame(outer, bg=BG)
            row.pack(anchor="w", fill="x")

            # Circle avatar
            av = circle_canvas(row, 32, BG, CYAN_DARK, "✦", CYAN, 9)
            av.pack(side="left", anchor="n", pady=4)

            right = tk.Frame(row, bg=BG)
            right.pack(side="left", padx=(10,50), fill="x", expand=True)

            # Estimate bubble size
            lines = content.count("\n") + 1
            bw    = 460
            bh    = max(lines * 22 + 24, 52)
            # rough line wrap estimate
            for para in content.split("\n"):
                bh += (len(para) // 55) * 20

            bc = tk.Canvas(right, width=bw, height=bh, bg=BG,
                           highlightthickness=0)
            bc.pack(anchor="w")
            rrect(bc, 0, 0, bw, bh, 18, fill=GLASS, outline="")
            # subtle border
            rrect(bc, 0, 0, bw, bh, 18, fill="", outline=BORDER_LT)
            bc.create_text(16, 14, text=content,
                           fill=TEXT, font=(FONT, 11),
                           width=bw-28, justify="left", anchor="nw")

            if time_str:
                tk.Label(right, text=time_str, font=(FONT, 7),
                         bg=BG, fg=DIM).pack(anchor="w", pady=(4,0))

    def _typing_indicator(self):
        wrap = tk.Frame(self.msg_inner, bg=BG)
        wrap.pack(fill="x", padx=16, pady=5)
        row  = tk.Frame(wrap, bg=BG)
        row.pack(anchor="w")
        av   = circle_canvas(row, 32, BG, CYAN_DARK, "✦", CYAN, 9)
        av.pack(side="left", anchor="n", pady=4)
        self._typing_lbl = tk.Label(row, text="  ●  ●  ●",
                                     font=(FONT, 12), bg=BG, fg=CYAN_DIM, padx=10)
        self._typing_lbl.pack(side="left", pady=8)
        self._typing_wrap = wrap
        self._animate_typing(0)
        self.root.after(80, self._scroll_bottom)

    def _animate_typing(self, step):
        if not self._typing: return
        frames = ["  ●        ", "     ●     ", "        ●  "]
        try:
            self._typing_lbl.config(text=frames[step % 3])
            self.root.after(350, lambda: self._animate_typing(step+1))
        except: pass

    def _remove_typing(self):
        self._typing = False
        try: self._typing_wrap.destroy()
        except: pass

    def _scroll_bottom(self):
        self.msg_canvas.update_idletasks()
        self.msg_canvas.yview_moveto(1.0)

    # ── SEND ──────────────────────────────────────────────────────────
    def _on_enter(self, e):
        if e.state & 0x1: return   # shift+enter = newline
        self._send()
        return "break"

    def _send_text(self, text):
        self.inp.delete("1.0","end")
        self.inp.insert("1.0", text)
        self._send()

    def _send(self):
        if not self.api_key: self._ask_api_key(); return
        text = self.inp.get("1.0","end").strip()
        if not text or self._typing: return
        self.inp.delete("1.0","end")

        chat = self._get_chat(self.active_id)
        if not chat: return

        now = datetime.now().strftime("%H:%M")
        chat["messages"].append({"role":"user","content":text,"time":now})
        if len(chat["messages"]) == 1:
            chat["title"] = text[:40] + ("…" if len(text)>40 else "")
            self.chat_title.config(text=chat["title"])
        self.chat_sub.config(text=f"{len(chat['messages'])} messages")
        self._save_data()
        self._bubble("user", text, now)
        self._refresh_sidebar()
        self.root.after(60, self._scroll_bottom)

        self._typing = True
        self._typing_indicator()

        msgs = [{"role":m["role"],"content":m["content"]} for m in chat["messages"]]

        def call():
            try:
                reply = call_gemini(self.api_key, msgs)
                self.root.after(0, lambda: self._on_reply(reply))
            except urllib.error.HTTPError as ex:
                try:    body = ex.read().decode("utf-8")
                except: body = ""
                err = f"API Error {ex.code}: {ex.reason}\n{body}"
                self.root.after(0, lambda e=err: self._on_reply(e, error=True))
            except Exception as ex:
                self.root.after(0, lambda e=str(ex): self._on_reply(e, error=True))

        threading.Thread(target=call, daemon=True).start()

    def _on_reply(self, content, error=False):
        self._remove_typing()
        chat = self._get_chat(self.active_id)
        if not chat: return
        now = datetime.now().strftime("%H:%M")
        chat["messages"].append({"role":"assistant","content":content,"time":now})
        self.chat_sub.config(text=f"{len(chat['messages'])} messages")
        self._save_data()
        self._bubble("assistant", content, now)
        self._refresh_sidebar()
        self.root.after(80, self._scroll_bottom)

    # ── API KEY DIALOG ────────────────────────────────────────────────
    def _ask_api_key(self):
        win = tk.Toplevel(self.root)
        win.title("API Key")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()
        win.geometry("440x360")
        win.update()

        tk.Frame(win, bg=CYAN, height=2).pack(fill="x")

        # Logo
        av = circle_canvas(win, 52, BG, CYAN_DARK, "✦", CYAN, 16)
        av.pack(pady=(24,8))
        tk.Label(win, text="GEMINI API KEY", font=(FONT, 13, "bold"),
                 bg=BG, fg=TEXT).pack()
        tk.Label(win, text="aistudio.google.com  →  Get API Key",
                 font=(FONT, 8), bg=BG, fg=TEXT2).pack(pady=(2,14))

        # Pill input
        ew_c = tk.Canvas(win, height=46, bg=BG, highlightthickness=0)
        ew_c.pack(fill="x", padx=30, pady=(0,6))
        ew_f = tk.Frame(ew_c, bg=GLASS2)
        entry = tk.Entry(ew_f, bg=GLASS2, fg=TEXT, insertbackground=CYAN,
                         font=(FONT, 11), bd=0, highlightthickness=0,
                         relief="flat", show="•")
        entry.pack(fill="x", padx=16, pady=12)
        if self.api_key: entry.insert(0, self.api_key)

        def draw_ew(focused=False):
            ew_c.delete("all")
            w = ew_c.winfo_width() or 380
            h = 46
            border = CYAN_DIM if focused else BORDER_LT
            rrect(ew_c, 0, 0, w, h, 23, fill=border, outline="")
            rrect(ew_c, 1, 1, w-1, h-1, 22, fill=GLASS2, outline="")
            ew_f.place(x=0, y=0, width=w, height=h)

        ew_c.bind("<Configure>", lambda e: draw_ew(False))
        entry.bind("<FocusIn>",  lambda e: draw_ew(True))
        entry.bind("<FocusOut>", lambda e: draw_ew(False))

        show_var = tk.BooleanVar(value=False)
        def toggle(): entry.config(show="" if show_var.get() else "•")
        tk.Checkbutton(win, text="Show key", variable=show_var, command=toggle,
                       bg=BG, fg=TEXT2, selectcolor=BG,
                       activebackground=BG).pack(pady=(0,6))

        status_lbl = tk.Label(win, text="", font=(FONT, 8), bg=BG, fg=TEXT2)
        status_lbl.pack(pady=(0,8))

        def test_key():
            key = entry.get().strip()
            if not key: return
            status_lbl.config(text="Testing...", fg=CYAN_DIM)
            win.update()
            import urllib.request as _ur, urllib.error as _ue, json as _j
            try:
                req = _ur.Request(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
                    headers={"User-Agent": "Chatify/1.0"})
                with _ur.urlopen(req, timeout=10) as r: _j.loads(r.read())
                status_lbl.config(text="✓  Key valid — ready to chat!", fg=GREEN)
            except _ue.HTTPError as ex:
                try: body = _j.loads(ex.read().decode())["error"]["message"]
                except: body = ex.reason
                status_lbl.config(text=f"✗  {ex.code}: {body}", fg=RED)
            except Exception as ex:
                status_lbl.config(text=f"✗  {ex}", fg=RED)

        def save():
            key = entry.get().strip()
            if not key:
                messagebox.showwarning("Missing","Please enter your API key"); return
            self.api_key = key; self._save_cfg(); win.destroy()
            if not self.chats: self._new_chat()

        # Buttons row
        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack(fill="x", padx=30)

        # Test pill
        t_c = tk.Canvas(btn_row, height=40, bg=BG, highlightthickness=0, cursor="hand2")
        t_c.pack(side="left", expand=True, fill="x", padx=(0,6))
        t_c.bind("<Configure>", lambda e: (t_c.delete("all"),
            rrect(t_c, 0, 0, t_c.winfo_width(), 40, 20, fill=GLASS3, outline=""),
            t_c.create_text(t_c.winfo_width()//2, 20, text="Test Key",
                            fill=CYAN, font=(FONT, 10))))
        t_c.bind("<ButtonRelease-1>", lambda e: test_key())

        # Save pill
        s_c = tk.Canvas(btn_row, height=40, bg=BG, highlightthickness=0, cursor="hand2")
        s_c.pack(side="right", expand=True, fill="x", padx=(6,0))
        s_c.bind("<Configure>", lambda e: (s_c.delete("all"),
            rrect(s_c, 0, 0, s_c.winfo_width(), 40, 20, fill=CYAN, outline=""),
            s_c.create_text(s_c.winfo_width()//2, 20, text="Save & Start",
                            fill=BG, font=(FONT, 10, "bold"))))
        s_c.bind("<ButtonRelease-1>", lambda e: save())

        entry.bind("<Return>", lambda e: save())
        entry.focus_set()


if __name__ == "__main__":
    root = tk.Tk()
    Chatify(root)
    root.mainloop()
