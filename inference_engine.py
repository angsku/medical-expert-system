# -*- coding: utf-8 -*-
"""
inference_engine.py —— 推理引擎
融合离散数学模块完成诊断：
  第 1 步  红旗规则检查（集合包含判断）→ 急诊提示
  第 2 步  症状-疾病匹配（交集 + 加权覆盖率 + Jaccard 相似度）→ 候选疾病排序
  第 3 步  鉴别诊断（症状集的对称差）→ 前两名疾病的鉴别要点
  第 4 步  并发症多级预警（并发症图 BFS 可达 + Warshall 传递闭包）→ 风险链
  第 5 步  推荐检查/科室/建议（复合关系 R1∘R2：症状→疾病→检查）
  另提供基于决策树的智能问诊会话 ConsultSession。
"""

from knowledge_base import (DISEASES, RED_FLAGS, build_complication_edges,
                            get_all_symptoms)
from discrete_math import (SetCalculator, Relation, Graph, warshall,
                           DecisionTree)


class InferenceEngine:
    """医疗专家系统推理引擎（正向推理 + 可解释输出）"""

    def __init__(self):
        # ---- 二元关系 ----
        # R1 ⊆ 症状×疾病：诊断关系
        self.r_symptom_disease = Relation("R1(症状→疾病)", {
            (s, d) for d, info in DISEASES.items() for s in info["symptoms"]})
        # R1⁻¹ ⊆ 疾病×症状：逆关系，诊断时从疾病反查它的症状全集
        self.r_disease_symptom = self.r_symptom_disease.inverse()
        # R2 ⊆ 疾病×检查：检查关系
        self.r_disease_test = Relation("R2(疾病→检查)", {
            (d, t) for d, info in DISEASES.items() for t in info["tests"]})
        # 复合关系 R1∘R2 ⊆ 症状×检查：输入某症状时应考虑的检查
        self.r_symptom_test = self.r_symptom_disease.compose(self.r_disease_test)

        # ---- 并发症有向图与传递闭包 ----
        self.complication_graph = Graph(directed=True)
        for u, v in build_complication_edges():
            self.complication_graph.add_edge(u, v)
        self.closure_nodes = self.complication_graph.nodes()
        n = len(self.closure_nodes)
        adj = [[1 if v in self.complication_graph.adj[u] else 0
                for v in self.closure_nodes] for u in self.closure_nodes]
        # Warshall 求传递闭包：闭包矩阵中 [i][j]=1 表示 i 经过若干级并发症可发展到 j
        self.closure_matrix = warshall(adj)

        # ---- 症状-疾病二部图（GUI 可视化用，无向） ----
        self.bipartite_graph = Graph(directed=False)
        for d, info in DISEASES.items():
            for s in info["symptoms"]:
                self.bipartite_graph.add_edge(s, d)

        # ---- 问诊决策树 ----
        self.decision_tree = DecisionTree(
            {d: set(info["symptoms"]) for d, info in DISEASES.items()})

        self.all_symptoms = get_all_symptoms()
        # 度中心性只算一次缓存起来：问诊选问时优先问"稀有"症状
        self.symptom_centrality = self.symptom_degree_centrality()

    # --------------------------------------------------------
    # 正向推理主流程
    # --------------------------------------------------------
    def diagnose(self, patient_symptoms):
        """输入患者症状集合，返回完整诊断结果（含解释）"""
        patient = set(patient_symptoms)

        # 第 1 步：红旗规则（"all"=子集判断 issubset，"any"=交集非空）
        red_flags = []
        for flag in RED_FLAGS:
            fs = flag["symptoms"]
            hit = (fs.issubset(patient) if flag["match"] == "all"
                   else bool(fs & patient))
            if hit:
                red_flags.append(flag)

        # 第 2 步：逐病匹配（集合交集 + 加权覆盖率 + Jaccard，排除症状扣减）
        candidates = []
        for disease, info in DISEASES.items():
            # 疾病的症状全集经逆关系 R1⁻¹ 查得（疾病→症状）
            disease_symptoms = self.r_disease_symptom.related_to(disease)
            hit = SetCalculator.intersection(patient, disease_symptoms)
            if not hit:
                continue
            coverage = SetCalculator.weighted_coverage(patient, info["symptoms"])
            jac = SetCalculator.jaccard(patient, info["symptoms"])
            # 排除症状：负权重按疾病总权重折算成扣减比例，下限 0
            exclusions_hit = sorted(s for s in info.get("exclude", {})
                                    if s in patient)
            if exclusions_hit:
                total_w = sum(info["symptoms"].values())
                penalty = sum(info["exclude"][s] for s in exclusions_hit) / total_w
                coverage = max(0.0, coverage + penalty)
            # 按权重降序列出命中症状，方便解释"为什么怀疑这个病"
            hit_sorted = sorted(hit, key=lambda s: -info["symptoms"][s])
            # 待观察症状 = 疾病症状 - 患者症状（差集），只保留典型症状（权重≥2）
            missing = SetCalculator.difference(disease_symptoms, patient)
            missed = sorted((s for s in missing if info["symptoms"][s] >= 2),
                            key=lambda s: -info["symptoms"][s])
            candidates.append({
                "disease": disease, "info": info,
                "coverage": coverage, "jaccard": jac,
                "hit_symptoms": hit_sorted, "missed_symptoms": missed,
                "exclusions_hit": exclusions_hit,
                "level": self._level(coverage),
            })
        candidates.sort(key=lambda c: (-c["coverage"], -c["jaccard"]))

        # 进入后续推理的疾病：覆盖率 ≥ 0.35（疑似及以上）
        suspected = [c for c in candidates if c["coverage"] >= 0.35]
        base = suspected if suspected else candidates[:1] if candidates else []

        # 第 3 步：前两名疑似疾病的鉴别诊断（对称差 A⊕B=(A-B)∪(B-A)）
        differential = None
        if len(base) >= 2:
            a, b = base[0]["disease"], base[1]["disease"]
            sym_diff = SetCalculator.symmetric_difference(
                DISEASES[a]["symptoms"], DISEASES[b]["symptoms"])
            only_a = SetCalculator.intersection(sym_diff, DISEASES[a]["symptoms"])
            only_b = SetCalculator.difference(sym_diff, DISEASES[a]["symptoms"])
            differential = {
                "a": a, "b": b,
                "only_in_a": sorted(only_a), "only_in_b": sorted(only_b),
            }

        # 第 4 步：并发症多级预警（图 BFS 求可达及步数）
        complication_warnings = []
        warned = set()                      # (起点, 终点) 去重
        for c in base:
            reach = self.complication_graph.bfs_reachable(c["disease"])
            for node, steps in sorted(reach.items(), key=lambda x: x[1]):
                if steps == 0 or (c["disease"], node) in warned:
                    continue
                warned.add((c["disease"], node))
                complication_warnings.append({
                    "from": c["disease"], "to": node, "steps": steps,
                    "chain": self._chain_text(c["disease"], node, steps)})

        # 第 5 步：推荐检查/科室/建议（复合关系 R1∘R2 查询 + 并集汇总）
        tests, departments, advices = [], [], []
        for c in base:
            tests.extend(t for s in c["hit_symptoms"]
                         for t in self.r_symptom_test.related_to(s)
                         if t in c["info"]["tests"])
            departments.append(c["info"]["department"])
            advices.append(f"【{c['disease']}】{c['info']['advice']}")
        seen, ordered_tests = set(), []
        for t in tests:
            if t not in seen:
                seen.add(t)
                ordered_tests.append(t)

        return {
            "input": sorted(patient),
            "red_flags": red_flags,
            "candidates": candidates,
            "suspected_names": [c["disease"] for c in base],
            "differential": differential,
            "complication_warnings": complication_warnings,
            "tests": ordered_tests,
            "departments": [d for d in dict.fromkeys(departments)],
            "advices": [a for a in dict.fromkeys(advices)],
        }

    @staticmethod
    def _level(coverage):
        """按覆盖率划分可疑等级"""
        if coverage >= 0.6:
            return "高度疑似"
        if coverage >= 0.35:
            return "疑似"
        return "需留意"

    def _chain_text(self, start, end, steps):
        """在并发症图上重建 start→…→end 的最短推理链（BFS 路径回溯）"""
        if steps == 1:
            return f"{start} → {end}"
        # BFS 记录前驱，回溯出一条路径
        prev = {start: None}
        queue = [start]
        while queue:
            u = queue.pop(0)
            for v in self.complication_graph.adj.get(u, ()):
                if v not in prev:
                    prev[v] = u
                    if v == end:
                        path = [end]
                        while prev[path[-1]] is not None:
                            path.append(prev[path[-1]])
                        return " → ".join(reversed(path))
                    queue.append(v)
        return f"{start} → {end}"

    # --------------------------------------------------------
    # 知识库查询（供 GUI 使用）
    # --------------------------------------------------------
    def symptom_degree_centrality(self):
        """症状节点的度中心性：值越低的症状越稀有，鉴别价值越高"""
        centrality = self.bipartite_graph.degree_centrality()
        return {s: c for s, c in centrality.items() if s in set(self.all_symptoms)}

    def transitive_closure_pairs(self):
        """从 Warshall 闭包矩阵中取出 (i, j, 步数不可得) 对，供知识库页展示多级链"""
        pairs = []
        for i, u in enumerate(self.closure_nodes):
            for j, v in enumerate(self.closure_nodes):
                if self.closure_matrix[i][j] and i != j:
                    reach = self.complication_graph.bfs_reachable(u)
                    pairs.append((u, v, reach.get(v, "?")))
        return pairs


class ConsultSession:
    """智能问诊会话：决策树驱动的逐题问答"""

    def __init__(self, engine):
        self.engine = engine
        self.reset()

    def reset(self):
        self.candidates = set(DISEASES)
        self.asked = set()
        self.history = []                  # [(症状, 回答, 分裂后候选数)]
        self.finished = False

    def current_question(self):
        """当前应问的症状；无法再分裂或已收敛时返回 None"""
        if self.finished or len(self.candidates) <= 1:
            self.finished = True
            return None
        symptom = self.engine.decision_tree.best_question(
            self.candidates, self.asked, self.engine.symptom_centrality)
        if symptom is None:
            self.finished = True
        return symptom

    def answer(self, answer):
        """answer ∈ {"yes","no","unknown"}；返回更新后的候选疾病列表"""
        symptom = self.engine.decision_tree.best_question(
            self.candidates, self.asked, self.engine.symptom_centrality)
        if symptom is None:
            self.finished = True
            return sorted(self.candidates)
        self.asked.add(symptom)
        self.candidates = self.engine.decision_tree.split(
            symptom, self.candidates, answer)
        self.history.append((symptom, answer, len(self.candidates)))
        if not self.candidates or len(self.candidates) <= 1:
            self.finished = True
        return sorted(self.candidates)
