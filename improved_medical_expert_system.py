# -*- coding: utf-8 -*-
"""
improved_medical_expert_system.py —— 改进版医疗专家系统主程序（tkinter GUI）
四个功能页：
  1. 症状自诊：分组勾选症状 → 推理引擎正向推理 → 彩色诊断报告
  2. 推理可视化：症状-疾病-并发症三层推理图（Canvas 自绘），诊断后高亮推理路径
  3. 智能问诊：决策树驱动的一问一答，实时收窄候选疾病
  4. 知识库浏览：全部规则 + 症状度中心性 + 传递闭包多级风险链
仅使用 Python 标准库，无第三方依赖。
"""

import tkinter as tk
from tkinter import ttk, messagebox

from knowledge_base import (DISEASES, SYMPTOM_GROUPS, DISCLAIMER,
                            symptom_question)
from inference_engine import InferenceEngine, ConsultSession

# ---------- 配色（医疗风格） ----------
C_BG = "#f0f6fa"          # 页面底色
C_HEADER = "#1d6fa5"      # 顶部横幅
C_CARD = "#ffffff"        # 卡片底色
C_EDGE = "#b8c4cc"        # 普通边
C_ACTIVE = "#2a7fbf"      # 激活边/主色
C_SYMPTOM = "#d8f3dc"     # 症状节点
C_SYMPTOM_BD = "#2d6a4f"
C_COMP = "#ffe8cc"        # 并发症节点
C_COMP_BD = "#e76f51"
LEVEL_COLORS = {"高度疑似": "#c0392b", "疑似": "#d68910", "需留意": "#5d6d7e",
                "common": "#2a7fbf", "serious": "#c0392b"}
FONT = "Microsoft YaHei UI"


class MedicalExpertSystemApp:
    def __init__(self, root):
        self.root = root
        self.root.title("医疗专家系统（离散数学改进版）")
        self.root.geometry("1380x880")
        self.root.minsize(1200, 700)

        self.engine = InferenceEngine()
        self.session = ConsultSession(self.engine)
        self.last_result = None          # 最近一次诊断结果（可视化页共用）
        self.symptom_vars = {}           # {症状: BooleanVar}

        self._build_style()
        self._build_header()
        self._build_statusbar()          # 先占底部，notebook 才拿不到整片剩余空间
        self._build_notebook()

    # ======================================================
    # 基础框架
    # ======================================================
    def _build_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=(FONT, 10))
        style.configure("TNotebook", background=C_BG, borderwidth=0)
        style.configure("TNotebook.Tab", font=(FONT, 10, "bold"), padding=(14, 6))
        style.map("TNotebook.Tab", background=[("selected", C_ACTIVE)],
                  foreground=[("selected", "#ffffff")])
        style.configure("TButton", font=(FONT, 10), padding=(10, 4))
        # 主操作按钮：蓝底白字，悬停加深
        style.configure("Start.TButton", font=(FONT, 11, "bold"), padding=(18, 6),
                        background=C_ACTIVE, foreground="#ffffff")
        style.map("Start.TButton",
                  background=[("active", "#175a87"), ("pressed", "#124a70")],
                  foreground=[("active", "#ffffff"), ("pressed", "#ffffff")])
        style.configure("TLabelframe", background=C_CARD)
        style.configure("TLabelframe.Label", font=(FONT, 10, "bold"))
        style.configure("Treeview", font=(FONT, 9), rowheight=26)
        style.configure("Treeview.Heading", font=(FONT, 9, "bold"))
        style.map("Treeview", background=[("selected", "#cfe4f2")],
                  foreground=[("selected", "#20323f")])

    def _build_header(self):
        header = tk.Frame(self.root, bg=C_HEADER)
        header.pack(fill="x")
        tk.Label(header, text="医疗专家系统", font=(FONT, 17, "bold"),
                 bg=C_HEADER, fg="#ffffff").pack(side="left", padx=16, pady=10)
        tk.Label(header, text="集合论 · 二元关系 · 图论 · 树 融合推理",
                 font=(FONT, 10), bg=C_HEADER, fg="#cfe6f5").pack(side="left", pady=10)
        tk.Label(header, text="实训作品，仅供参考，不能替代医师诊断",
                 font=(FONT, 9), bg=C_HEADER, fg="#f5d6c0").pack(side="right", padx=16)

    def _build_notebook(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True)
        self.tab_diagnose = tk.Frame(self.nb, bg=C_BG)
        self.tab_viz = tk.Frame(self.nb, bg=C_BG)
        self.tab_consult = tk.Frame(self.nb, bg=C_BG)
        self.tab_kb = tk.Frame(self.nb, bg=C_BG)
        self.nb.add(self.tab_diagnose, text=" ① 症状自诊 ")
        self.nb.add(self.tab_viz, text=" ② 推理可视化 ")
        self.nb.add(self.tab_consult, text=" ③ 智能问诊 ")
        self.nb.add(self.tab_kb, text=" ④ 知识库 ")
        self._build_tab_diagnose()
        self._build_tab_viz()
        self._build_tab_consult()
        self._build_tab_kb()

    def _build_statusbar(self):
        bar = tk.Label(self.root, text=DISCLAIMER, anchor="w", bg="#e8eef4",
                       fg="#5d6d7e", font=(FONT, 9))
        bar.pack(fill="x", side="bottom")

    # ======================================================
    # 页面一：症状自诊
    # ======================================================
    def _build_tab_diagnose(self):
        left = tk.Frame(self.tab_diagnose, bg=C_BG)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.configure(width=360)
        left.pack_propagate(False)
        right = tk.Frame(self.tab_diagnose, bg=C_BG)
        right.pack(side="left", fill="both", expand=True, padx=(5, 10), pady=10)

        tk.Label(left, text="① 请勾选当前症状", font=(FONT, 11, "bold"),
                 bg=C_BG).pack(anchor="w")

        # 症状搜索框：34 个症状按关键字过滤，方便快速定位
        search_var = tk.StringVar()
        search_row = tk.Frame(left, bg=C_BG)
        search_row.pack(fill="x", pady=(4, 2))
        tk.Label(search_row, text="搜索：", font=(FONT, 9), bg=C_BG,
                 fg="#5d6d7e").pack(side="left")
        ttk.Entry(search_row, textvariable=search_var).pack(
            side="left", fill="x", expand=True, padx=(2, 0))
        self.symptom_widgets = {}           # 症状 -> Checkbutton
        self.group_boxes, self.group_members = [], []

        # 症状勾选区（可滚动）
        scroll_area = tk.Frame(left, bg=C_CARD)
        scroll_area.pack(fill="both", expand=True)
        canvas = tk.Canvas(scroll_area, bg=C_CARD, highlightthickness=0)
        vsb = ttk.Scrollbar(scroll_area, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=C_CARD)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw", width=320)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        for group, members in SYMPTOM_GROUPS.items():
            box = ttk.Labelframe(inner, text=group, padding=(6, 4))
            box.pack(fill="x", pady=4, padx=4)
            self.group_boxes.append(box)
            self.group_members.append(list(members))
            for i, symptom in enumerate(members):
                var = tk.BooleanVar()
                self.symptom_vars[symptom] = var
                cb = tk.Checkbutton(box, text=symptom, variable=var,
                                    bg=C_CARD, activebackground=C_CARD,
                                    font=(FONT, 9), anchor="w")
                cb.grid(row=i % 4, column=i // 4, sticky="w", padx=2, ipady=1)
                self.symptom_widgets[symptom] = cb
            for col in range(2):
                box.columnconfigure(col, weight=1)
        search_var.trace_add(
            "write", lambda *a: self._filter_symptoms(search_var.get()))

        # 鼠标滚轮仅在指针位于勾选区内时生效
        canvas.bind("<Enter>", lambda e: canvas.bind_all(
            "<MouseWheel>", lambda ev: canvas.yview_scroll(-ev.delta // 120, "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # 操作按钮与已选症状
        ops = tk.Frame(left, bg=C_BG)
        ops.pack(fill="x", pady=6)
        ttk.Button(ops, text="开始诊断", style="Start.TButton",
                   command=self.on_diagnose).pack(side="left", expand=True,
                                                  fill="x", padx=(0, 4))
        ttk.Button(ops, text="清空", command=self.on_clear).pack(
            side="left", expand=True, fill="x")
        self.sel_label = tk.Label(left, text="已选症状：无", font=(FONT, 9),
                                  bg=C_BG, fg="#5d6d7e", wraplength=340,
                                  justify="left")
        self.sel_label.pack(anchor="w", pady=(4, 0))

        # 右：诊断报告（限宽居中，宽窗口下避免"内容挤左、右侧大片空白"）
        tk.Label(right, text="② 诊断报告", font=(FONT, 11, "bold"),
                 bg=C_BG).pack(anchor="w")
        wrap = tk.Frame(right, bg=C_BG)
        wrap.pack(fill="both", expand=True)
        wrap.columnconfigure(0, weight=1)      # 左弹性留白
        wrap.columnconfigure(2, weight=1)      # 右弹性留白
        wrap.rowconfigure(0, weight=1)
        self.report = tk.Text(wrap, bg=C_CARD, font=(FONT, 10), wrap="word",
                              relief="flat", padx=14, pady=10, spacing2=4,
                              spacing3=6, state="disabled", width=88, height=30)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.report.yview)
        self.report.configure(yscrollcommand=sb.set)
        self.report.grid(row=0, column=1, sticky="nsew")
        sb.grid(row=0, column=2, sticky="ns")
        for tag, kw in {
            "h1": {"font": (FONT, 12, "bold"), "foreground": C_HEADER},
            "h2": {"font": (FONT, 10, "bold"), "foreground": "#20323f"},
            "red": {"foreground": "#c0392b", "font": (FONT, 10, "bold")},
            "orange": {"foreground": "#d68910"},
            "green": {"foreground": "#1e8449"},
            "gray": {"foreground": "#7b8a97"},
            "blue": {"foreground": C_ACTIVE},
        }.items():
            self.report.tag_configure(tag, **kw)
        self._render_welcome()                # 初始欢迎卡片

    def _filter_symptoms(self, text):
        """按关键字过滤症状勾选列表，整组无匹配时隐藏该分组"""
        text = text.strip()
        for box, members in zip(self.group_boxes, self.group_members):
            any_visible = False
            for symptom in members:
                cb = self.symptom_widgets[symptom]
                if not text or text in symptom:
                    cb.grid()
                    any_visible = True
                else:
                    cb.grid_remove()
            if any_visible:
                box.pack(fill="x", pady=4, padx=4)
            else:
                box.pack_forget()

    def selected_symptoms(self):
        return [s for s, v in self.symptom_vars.items() if v.get()]

    def _update_sel_label(self, chosen):
        """已选症状提示：带计数，方便确认勾选数量"""
        if chosen:
            self.sel_label.config(
                text=f"已选症状（{len(chosen)} 项）：{'、'.join(chosen)}")
        else:
            self.sel_label.config(text="已选症状：无")

    def _render_welcome(self):
        """报告区欢迎卡片：未诊断/清空时的填充界面"""
        box = self.report
        box.config(state="normal")
        box.delete("1.0", "end")
        for tag, kw in {
            "w_title": {"font": (FONT, 17, "bold"), "foreground": C_HEADER,
                        "justify": "center", "spacing1": 14},
            "w_sub": {"font": (FONT, 10), "foreground": "#5d6d7e",
                      "justify": "center", "spacing1": 3},
            "w_head": {"font": (FONT, 12, "bold"), "foreground": "#20323f",
                       "justify": "center", "spacing1": 16},
            "w_stat": {"font": (FONT, 10, "bold"), "foreground": C_ACTIVE,
                       "justify": "center", "spacing1": 4},
            "w_hint": {"font": (FONT, 9), "foreground": "#7b8a97",
                       "justify": "center", "spacing1": 18},
        }.items():
            box.tag_configure(tag, **kw)
        box.insert("end", "\n\n\n医疗专家系统\n", "w_title")
        box.insert("end", "集合论 · 二元关系 · 图论 · 树 融合推理\n", "w_sub")
        box.insert("end", "─" * 30 + "\n", "w_sub")
        box.insert("end", "三步完成自诊\n", "w_head")
        box.insert("end", "① 在左侧勾选当前症状（顶部搜索框可过滤）\n", "w_sub")
        box.insert("end", "② 点击「开始诊断」\n", "w_sub")
        box.insert("end", "③ 右侧生成彩色诊断报告\n", "w_sub")
        box.insert("end", "系统内置\n", "w_head")
        box.insert("end", "12 种疾病 · 34 个症状（三级权重） · 4 条急诊红旗规则\n", "w_stat")
        box.insert("end", "鉴别诊断（对称差） · 推荐检查（复合关系 R1∘R2）\n", "w_stat")
        box.insert("end", "并发症多级预警（Warshall 传递闭包）\n", "w_stat")
        box.insert("end", "切换上方页签：推理可视化 / 智能问诊 / 知识库\n", "w_hint")
        box.config(state="disabled")

    def on_clear(self):
        for v in self.symptom_vars.values():
            v.set(False)
        self._update_sel_label([])
        # 报告区同步清空回欢迎卡片，推理图回全景
        self.last_result = None
        self._render_welcome()
        self.draw_inference_graph()

    def on_diagnose(self):
        chosen = self.selected_symptoms()
        self._update_sel_label(chosen)
        if not chosen:
            messagebox.showinfo("提示", "请先勾选至少一个症状")
            return
        self.last_result = self.engine.diagnose(chosen)
        self.render_report(self.last_result)
        self.draw_inference_graph()

    def render_report(self, r):
        """把诊断结果渲染成彩色报告文本"""
        box = self.report
        box.config(state="normal")
        box.delete("1.0", "end")

        box.insert("end", "【输入症状】", "h2")
        box.insert("end", "、".join(r["input"]) + "\n\n")

        for flag in r["red_flags"]:
            level = "⚠ 急诊提示" if flag["level"] == "emergency" else "⚠ 风险提示"
            box.insert("end", level, "red")
            box.insert("end", f"  {flag['message']}\n")
        if r["red_flags"]:
            box.insert("end", "\n")

        if not r["candidates"]:
            box.insert("end", "【诊断结论】", "h2")
            box.insert("end", "未匹配到任何已知疾病，建议进行常规体检或就诊。\n")
        else:
            box.insert("end", "【诊断结论】（按加权覆盖率排序）\n", "h2")
            for i, c in enumerate(r["candidates"][:5], 1):
                color = LEVEL_COLORS[c["level"]]
                pct = round(c["coverage"] * 100)
                bar = "█" * max(1, int(c["coverage"] * 22))
                tag = f"lvl{i}"
                box.tag_configure(tag, foreground=color, font=(FONT, 11, "bold"))
                box.insert("end", f"{i}. {c['disease']}  {c['level']}"
                                   f"  置信度 {pct}%\n", tag)
                box.insert("end", f"   {bar}\n", tag)
                box.insert("end", "   命中症状：", "h2")
                box.insert("end", "、".join(c["hit_symptoms"]) + "\n", "green")
                if c["exclusions_hit"]:
                    box.insert("end", "   排除症状：", "h2")
                    box.insert("end",
                               "、".join(c["exclusions_hit"]) +
                               "（该病通常不出现，置信度已下调）\n", "orange")
                if c["missed_symptoms"]:
                    box.insert("end", "   待观察症状：", "h2")
                    box.insert("end", "、".join(c["missed_symptoms"]) + "\n", "gray")
                if c["info"]["urgency"] == "serious":
                    box.insert("end", "   ※ 该病可能进展较快，建议尽快就医\n", "red")
            box.insert("end", "\n")

        if r["differential"]:
            d = r["differential"]
            box.insert("end", "【鉴别诊断】（前两名疾病的症状对称差）\n", "h2")
            box.insert("end", f"  仅「{d['a']}」具有：", "h2")
            box.insert("end", "、".join(d["only_in_a"]) or "无", "blue")
            box.insert("end", f"\n  仅「{d['b']}」具有：", "h2")
            box.insert("end", "、".join(d["only_in_b"]) or "无", "blue")
            box.insert("end", "\n  两者症状高度重叠时，应结合病史与检查进一步区分。\n\n", "gray")

        if r["complication_warnings"]:
            box.insert("end", "【并发症风险预警】（并发症图传递闭包推导）\n", "h2")
            for w in r["complication_warnings"]:
                box.insert("end", f"  {w['chain']}", "orange")
                box.insert("end", f"（{w['steps']}级风险链）\n")
            box.insert("end", "\n")

        if r["tests"]:
            box.insert("end", "【推荐检查】（复合关系 R1∘R2 汇总）\n", "h2")
            for t in r["tests"]:
                box.insert("end", f"  · {t}\n")
        if r["departments"]:
            box.insert("end", "\n【建议就诊科室】\n", "h2")
            box.insert("end", "  " + "；".join(r["departments"]) + "\n")
        if r["advices"]:
            box.insert("end", "\n【处置建议】\n", "h2")
            for a in r["advices"]:
                box.insert("end", f"  · {a}\n", "gray")

        box.insert("end", "\n" + DISCLAIMER + "\n", "gray")
        box.config(state="disabled")

    # ======================================================
    # 页面二：推理可视化
    # ======================================================
    def _build_tab_viz(self):
        top = tk.Frame(self.tab_viz, bg=C_BG)
        top.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(top, text="症状 → 疾病 → 并发症 推理图", font=(FONT, 11, "bold"),
                 bg=C_BG).pack(side="left")
        tk.Label(top, text="（诊断后自动高亮推理路径；未诊断时展示知识库全景）",
                 font=(FONT, 9), bg=C_BG, fg="#5d6d7e").pack(side="left", padx=8)

        wrap = tk.Frame(self.tab_viz, bg=C_BG)
        wrap.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.viz_canvas = tk.Canvas(wrap, bg="#fbfdfe", highlightthickness=0)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.viz_canvas.yview)
        hsb = ttk.Scrollbar(wrap, orient="horizontal",
                            command=self.viz_canvas.xview)
        self.viz_canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.viz_canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        self.draw_inference_graph()

    def draw_inference_graph(self):
        """三层推理图：左列症状、中列疾病、右列并发症。
        有诊断结果时只画本次推理涉及的节点并高亮，否则画全景图"""
        cv = self.viz_canvas
        cv.delete("all")
        r = self.last_result
        x_sym, x_dis, x_comp = 110, 520, 940
        w, h, row_gap = 150, 30, 46

        def node(x, y, text, fill, outline, active=False):
            cv.create_rectangle(x - w / 2, y - h / 2, x + w / 2, y + h / 2,
                                fill=fill, outline=outline,
                                width=2 if active else 1)
            cv.create_text(x, y, text=text, font=(FONT, 9), width=w - 8)

        def edge(x1, y1, x2, y2, active=False, dashed=False):
            cv.create_line(x1, y1, x2, y2,
                           fill=C_ACTIVE if active else C_EDGE,
                           width=2 if active else 1,
                           dash=(4, 3) if dashed else None,
                           arrow=tk.LAST)

        if r is None:
            # 全景图：疾病层 + 每病权重最高的前三个典型症状
            cv.create_text(70, 24, text="典型症状", font=(FONT, 10, "bold"),
                           fill=C_SYMPTOM_BD)
            cv.create_text(x_dis, 24, text="疾病层（12 种）",
                           font=(FONT, 10, "bold"), fill=C_HEADER)
            ordered = sorted(DISEASES.items(),
                             key=lambda kv: -sum(kv[1]["symptoms"].values()))
            for i, (disease, info) in enumerate(ordered):
                y = 70 + i * row_gap
                color = LEVEL_COLORS[info["urgency"]]
                node(x_dis, y, f"{disease}（{len(info['symptoms'])}个症状）",
                     "#fdecea" if color == "#c0392b" else "#eaf3fa", color)
                top3 = sorted(info["symptoms"],
                              key=lambda s: -info["symptoms"][s])[:3]
                for j, s in enumerate(top3):
                    ys = y - 14 + j * 14
                    cv.create_text(x_dis - w / 2 - 10, ys, text=s,
                                   font=(FONT, 8), fill="#5d6d7e", anchor="e")
            cv.configure(scrollregion=(0, 0, 1150, 70 + 12 * row_gap + 40))
            return

        # ---- 本次推理图 ----
        cv.create_text(x_sym, 24, text="输入症状", font=(FONT, 10, "bold"),
                       fill=C_SYMPTOM_BD)
        cv.create_text(x_dis, 24, text="候选疾病（含置信度）",
                       font=(FONT, 10, "bold"), fill=C_HEADER)
        cv.create_text(x_comp, 24, text="并发症（传递闭包）",
                       font=(FONT, 10, "bold"), fill=C_COMP_BD)

        cands = r["candidates"][:5]
        sym_ys = {}
        for i, s in enumerate(r["input"]):
            y = 70 + i * row_gap
            node(x_sym, y, s, C_SYMPTOM, C_SYMPTOM_BD, active=True)
            sym_ys[s] = y
        dis_ys = {}
        for i, c in enumerate(cands):
            y = 70 + i * row_gap
            color = LEVEL_COLORS[c["level"]]
            fill = {"#c0392b": "#fdecea", "#d68910": "#fdf3e2"}.get(
                color, "#eef2f5")
            node(x_dis, y, f"{c['disease']} {round(c['coverage'] * 100)}%",
                 fill, color)
            dis_ys[c["disease"]] = y
        for c in cands:
            for s in c["hit_symptoms"]:
                if s in sym_ys:
                    edge(x_sym + w / 2, sym_ys[s], x_dis - w / 2,
                         dis_ys[c["disease"]], active=c["coverage"] >= 0.35)
        comp_ys = {}
        for warn in r["complication_warnings"]:
            # 同名并发症只画一个节点，多个来源疾病的边汇到同一节点
            name = warn["to"]
            if name not in comp_ys:
                y = 70 + len(comp_ys) * row_gap
                node(x_comp, y, name, C_COMP, C_COMP_BD,
                     active=warn["steps"] >= 2)
                comp_ys[name] = y
            src_y = dis_ys.get(warn["from"])
            if src_y:
                edge(x_dis + w / 2, src_y, x_comp - w / 2, comp_ys[name],
                     active=warn["steps"] >= 2, dashed=True)
        total_rows = max(len(r["input"]), len(cands), len(comp_ys))
        cv.configure(scrollregion=(0, 0, 1150, 70 + total_rows * row_gap + 40))

    # ======================================================
    # 页面三：智能问诊（决策树）
    # ======================================================
    def _build_tab_consult(self):
        self.tab_consult.columnconfigure(0, weight=1)
        self.tab_consult.columnconfigure(1, weight=0)
        self.tab_consult.rowconfigure(0, weight=1)

        card = tk.Frame(self.tab_consult, bg=C_CARD)
        card.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        tk.Label(card, text="智能问诊（决策树逐题收窄候选疾病）",
                 font=(FONT, 12, "bold"), bg=C_CARD, fg=C_HEADER).pack(pady=(16, 4))
        self.cand_label = tk.Label(card, text="", font=(FONT, 10),
                                   bg=C_CARD, fg="#5d6d7e")
        self.cand_label.pack()
        # 候选疾病实时名单：演示时能看到候选集一轮轮收窄的过程
        self.cand_names = tk.Label(card, text="", font=(FONT, 10),
                                   bg="#f4f8fb", fg=C_HEADER,
                                   wraplength=560, justify="left",
                                   relief="flat", padx=10, pady=6)
        self.cand_names.pack(fill="x", padx=24, pady=(2, 0))
        self.q_label = tk.Label(card, text="", font=(FONT, 14, "bold"),
                                bg=C_CARD, fg="#20323f", wraplength=560)
        self.q_label.pack(fill="both", expand=True, pady=18)
        btns = tk.Frame(card, bg=C_CARD)
        btns.pack(pady=(0, 8))
        for text, ans, color in (("是", "yes", "#1e8449"),
                                 ("否", "no", "#c0392b"),
                                 ("不确定", "unknown", "#7b8a97")):
            tk.Button(btns, text=text, font=(FONT, 11, "bold"),
                      width=9, relief="groove", bg=color, fg="#ffffff",
                      activebackground=color,
                      command=lambda a=ans: self.on_answer(a)
                      ).pack(side="left", padx=10)
        ttk.Button(card, text="重新开始问诊",
                   command=self.reset_consult).pack(pady=(4, 14))

        hist = tk.Frame(self.tab_consult, bg=C_BG)
        hist.grid(row=0, column=1, sticky="ns", padx=(5, 10), pady=10)
        tk.Label(hist, text="问答记录 / 候选疾病", font=(FONT, 10, "bold"),
                 bg=C_BG).pack(anchor="w", pady=(0, 4))
        self.hist_text = tk.Text(hist, bg=C_CARD, font=(FONT, 9), wrap="word",
                                 relief="flat", padx=10, pady=8, spacing2=3,
                                 width=34)
        self.hist_text.pack(fill="both", expand=True)
        self.hist_text.tag_configure(
            "h2", font=(FONT, 10, "bold"))
        self.hist_text.tag_configure("blue", foreground=C_ACTIVE,
                                     font=(FONT, 10, "bold"))
        self.reset_consult()

    def reset_consult(self):
        self.session.reset()
        self.hist_text.delete("1.0", "end")
        self.next_question()

    def next_question(self):
        s = self.session.current_question()
        n = len(self.session.candidates)
        self.cand_label.config(text=f"当前候选疾病：{n} 种")
        self.cand_names.config(
            text="、".join(sorted(self.session.candidates)) if n else "（无）")
        if s is None:
            self.q_label.config(text="问诊结束，结论见右侧记录")
            self.show_consult_result()
            return
        self.q_label.config(text=symptom_question(s))

    def on_answer(self, ans):
        if self.session.finished:
            return
        q = self.q_label.cget("text")
        label = {"yes": "是", "no": "否", "unknown": "不确定"}[ans]
        self.session.answer(ans)
        self.hist_text.insert("end", f"问：{q}\n答：{label}"
                                  f"（剩余候选 {len(self.session.candidates)}）\n\n")
        self.hist_text.see("end")
        self.next_question()

    def show_consult_result(self):
        cands = sorted(self.session.candidates)
        box = self.hist_text
        box.insert("end", "─" * 22 + "\n【问诊结论】\n", "h2")
        if not cands:
            box.insert("end", "根据您的回答未匹配到已知疾病，建议就诊检查。\n")
        else:
            for d in cands:
                info = DISEASES[d]
                box.insert("end", f"◆ {d}\n", "blue")
                box.insert("end", f"  建议检查：{'、'.join(info['tests'])}\n")
                box.insert("end", f"  就诊科室：{info['department']}\n")
                box.insert("end", f"  处置建议：{info['advice']}\n\n")
        box.see("end")

    # ======================================================
    # 页面四：知识库浏览
    # ======================================================
    def _build_tab_kb(self):
        left = tk.Frame(self.tab_kb, bg=C_BG)
        left.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)
        right = tk.Frame(self.tab_kb, bg=C_BG)
        right.pack(side="left", fill="y", padx=(5, 10), pady=10)

        tk.Label(left, text=f"疾病规则库（{len(DISEASES)} 种疾病）",
                 font=(FONT, 11, "bold"), bg=C_BG).pack(anchor="w")
        cols = ("disease", "symptoms", "tests", "dept", "comp", "urgency")
        self.kb_tree = ttk.Treeview(left, columns=cols, show="headings")
        headers = (("disease", "疾病", 110), ("symptoms", "症状（权重）", 330),
                   ("tests", "推荐检查", 170), ("dept", "科室", 120),
                   ("comp", "并发症", 150), ("urgency", "紧急度", 70))
        for key, text, width in headers:
            self.kb_tree.heading(key, text=text)
            self.kb_tree.column(key, width=width, anchor="w")
        self.kb_tree.pack(fill="both", expand=True)

        urgency_cn = {"common": "一般", "serious": "尽快就医"}
        for i, (d, info) in enumerate(DISEASES.items()):
            sym_text = "、".join(f"{s}({w})"
                                 for s, w in sorted(info["symptoms"].items(),
                                                    key=lambda kv: -kv[1]))
            # 斑马纹：隔行浅蓝底，长表格更好读
            tag = "stripe" if i % 2 else ""
            self.kb_tree.insert("", "end", tags=(tag,) if tag else (), values=(
                d, sym_text, "、".join(info["tests"]), info["department"],
                "、".join(info["complications"]),
                urgency_cn[info["urgency"]]))
        self.kb_tree.tag_configure("stripe", background="#f2f7fb")

        tk.Label(right, text="症状鉴别价值（度中心性升序）",
                 font=(FONT, 10, "bold"), bg=C_BG).pack(anchor="w")
        tk.Label(right, text="中心性越低越稀有，鉴别诊断价值越高",
                 font=(FONT, 8), bg=C_BG, fg="#5d6d7e").pack(anchor="w")
        cent_box = tk.Text(right, bg=C_CARD, font=(FONT, 9), height=12,
                           relief="flat", padx=10, pady=6)
        cent_box.pack(fill="x", pady=(2, 8))
        centrality = self.engine.symptom_degree_centrality()
        for s, c in sorted(centrality.items(), key=lambda kv: (kv[1], kv[0]))[:10]:
            diseases = sorted(self.engine.bipartite_graph.adj.get(s, ()))
            cent_box.insert("end", f"{s}（{c:.3f}，仅见于："
                                   f"{'、'.join(diseases) or '无'}）\n")
        cent_box.config(state="disabled")

        tk.Label(right, text="多级并发症风险链（传递闭包 ≥2 级）",
                 font=(FONT, 10, "bold"), bg=C_BG).pack(anchor="w")
        chain_box = tk.Text(right, bg=C_CARD, font=(FONT, 9),
                            relief="flat", padx=10, pady=6)
        chain_box.pack(fill="both", expand=True)
        for u, v, steps in self.engine.transitive_closure_pairs():
            if isinstance(steps, int) and steps >= 2:
                chain = self.engine._chain_text(u, v, steps)
                chain_box.insert("end", f"{chain}（{steps}级）\n")
        chain_box.config(state="disabled")


def main():
    try:                                   # Windows 高分屏下界面更清晰
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    MedicalExpertSystemApp(root)
    # 启动时窗口居中
    root.update_idletasks()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"+{(sw - root.winfo_width()) // 2}"
                  f"+{max(0, (sh - root.winfo_height()) // 2 - 20)}")
    root.mainloop()


if __name__ == "__main__":
    main()
