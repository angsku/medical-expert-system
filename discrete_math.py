# -*- coding: utf-8 -*-
"""
discrete_math.py —— 离散数学基础模块
把本项目用到的离散数学算法集中封装，供推理引擎调用：
  1. SetCalculator   集合论：交/并/差/对称差、Jaccard 相似度、加权覆盖率
  2. Relation        二元关系：布尔矩阵表示、复合关系 R1∘R2、逆关系 R^-1、Warshall 传递闭包
  3. Graph           图论：邻接表、BFS 可达集、连通分量、度中心性
  4. DecisionTree    树：按"鉴别力"选下一个问诊症状（决策树贪心建树，信息增益思想）
对应基础实训代码 3（集合）、4（关系与函数）、5（树）、6（图）。
"""


# ============================================================
# 一、集合论
# ============================================================
class SetCalculator:
    """集合运算工具：诊断匹配的核心"""

    @staticmethod
    def intersection(a, b):
        """交集 A∩B：患者症状与疾病症状的公共部分，即"命中症状" """
        return set(a) & set(b)

    @staticmethod
    def union(a, b):
        """并集 A∪B"""
        return set(a) | set(b)

    @staticmethod
    def difference(a, b):
        """差集 A-B：a 中有而 b 中没有的元素"""
        return set(a) - set(b)

    @staticmethod
    def symmetric_difference(a, b):
        """对称差 A⊕B=(A-B)∪(B-A)：两个集合各自的独有元素。
        诊断里用来做鉴别诊断——两种疾病的"鉴别症状"就是症状集的对称差"""
        return set(a) ^ set(b)

    @staticmethod
    def jaccard(a, b):
        """Jaccard 相似度 = |A∩B| / |A∪B|，衡量患者症状与疾病症状集的整体相似程度"""
        u = SetCalculator.union(a, b)
        if not u:
            return 0.0
        return len(set(a) & set(b)) / len(u)

    @staticmethod
    def weighted_coverage(patient_symptoms, weighted_target):
        """加权覆盖率 = Σ(命中症状的权重) / Σ(全部症状的权重)
        比普通 Jaccard 更聪明的地方：典型症状（权重 3）命中的贡献大，
        非特异症状（如乏力，权重 1）即使命中也只贡献 1 分"""
        total = sum(weighted_target.values())
        if total == 0:
            return 0.0
        hit = sum(w for s, w in weighted_target.items() if s in patient_symptoms)
        return hit / total


# ============================================================
# 二、二元关系
# ============================================================
class Relation:
    """二元关系 R ⊆ A×B，用序偶集合表示"""

    def __init__(self, name, pairs):
        self.name = name
        self.pairs = set(pairs)          # {(a,b), ...}

    def __contains__(self, item):
        return item in self.pairs

    def add(self, a, b):
        self.pairs.add((a, b))

    def domain(self):
        """定义域 dom(R)：所有第一元素"""
        return {a for a, _ in self.pairs}

    def range(self):
        """值域 ran(R)：所有第二元素"""
        return {b for _, b in self.pairs}

    def related_to(self, a):
        """给定 a，求所有满足 (a,b)∈R 的 b（关系下 a 的像）"""
        return {b for x, b in self.pairs if x == a}

    def inverse(self):
        """逆关系 R⁻¹ = {(b,a) | (a,b)∈R}"""
        return Relation(self.name + "⁻¹", {(b, a) for a, b in self.pairs})

    def compose(self, other):
        """复合关系 R∘S（先 R 后 S）：
        R ⊆ A×B，S ⊆ B×C，R∘S = {(a,c) | ∃b, (a,b)∈R 且 (b,c)∈S}
        诊断里：症状→疾病 关系 复合 疾病→检查 关系 = 症状→检查 的推荐关系"""
        composed = set()
        for a, b1 in self.pairs:
            for b2, c in other.pairs:
                if b1 == b2:
                    composed.add((a, c))
        return Relation(f"{self.name}∘{other.name}", composed)


def warshall(adj):
    """Warshall 算法求关系/图的传递闭包。
    adj: 布尔邻接矩阵（嵌套列表），返回 R^+ 的布尔矩阵。
    R^+ = R ∪ R² ∪ R³ ∪ ... 表示"多步可达"。
    并发症预警用：胃肠炎→脱水→电解质紊乱 是两步链，
    直接邻接只有一步，传递闭包能把所有多级风险链一次算全"""
    n = len(adj)
    reach = [row[:] for row in adj]          # 复制矩阵，不改动原数据
    for k in range(n):                        # 依次允许经过中间点 k
        for i in range(n):
            if reach[i][k]:                   # 小优化：i 到 k 不通则跳过内层循环
                for j in range(n):
                    if reach[k][j]:
                        reach[i][j] = 1       # i→k→j 可达
    return reach


# ============================================================
# 三、图论
# ============================================================
class Graph:
    """有向图/无向图：邻接表实现"""

    def __init__(self, directed=True):
        self.directed = directed
        self.adj = {}                          # {节点: {邻居,...}}

    def add_node(self, node):
        self.adj.setdefault(node, set())

    def add_edge(self, u, v):
        self.add_node(u)
        self.add_node(v)
        self.adj[u].add(v)
        if not self.directed:
            self.adj[v].add(u)

    def nodes(self):
        return list(self.adj)

    def bfs_reachable(self, start, max_depth=None):
        """广度优先搜索求 start 出发可达的所有节点及最短步数。
        max_depth 限制推理链长度；返回 {节点: 最短步数}"""
        depth = {start: 0}
        queue = [start]
        while queue:
            u = queue.pop(0)                   # list.pop(0) 实现先进先出
            if max_depth is not None and depth[u] >= max_depth:
                continue
            for v in self.adj.get(u, ()):
                if v not in depth:
                    depth[v] = depth[u] + 1
                    queue.append(v)
        return depth

    def degree(self, node):
        """节点度数（无向图）；有向图为出度+入度之和"""
        out_d = len(self.adj.get(node, ()))
        in_d = sum(1 for nbrs in self.adj.values() if node in nbrs)
        return out_d + in_d

    def degree_centrality(self):
        """度中心性 = 度数/(n-1)。症状节点的度中心性越低越"稀有"，
        稀有症状对鉴别诊断的价值越大（如味觉减退只在新冠规则中出现）"""
        n = len(self.adj)
        if n <= 1:
            return {node: 0.0 for node in self.adj}
        return {node: self.degree(node) / (n - 1) for node in self.adj}


# ============================================================
# 四、树
# ============================================================
class DecisionTree:
    """问诊决策树：每一轮从剩余候选疾病的症状中挑选"鉴别力最高"的症状提问，
    根据回答（是/否/不确定）把候选集分裂，直到能收敛。
    鉴别力用类似信息增益的指标：分裂后子集越小越纯，该症状增益越大。
    这是决策树学习（如 ID3）中贪心选择属性思想在问诊中的直接应用"""

    def __init__(self, disease_symptoms):
        """disease_symptoms: {疾病: 症状集合}"""
        self.disease_symptoms = disease_symptoms

    def split_score(self, symptom, candidates):
        """症状对当前候选集的分裂得分。
        候选中"有该症状"的疾病数记 p，"没有"的记 n：
        p=0 或 n=0 说明问了白问（区分不了任何疾病），得分 0；
        p 与 n 越均衡且都非零，说明该症状最能"劈开"候选集，得分越高"""
        p = sum(1 for d in candidates if symptom in self.disease_symptoms[d])
        n = len(candidates) - p
        if p == 0 or n == 0:
            return 0.0
        return min(p, n) / (p + n) + 1e-9      # 均衡度 ∈ (0, 0.5]，越大越好

    def best_question(self, candidates, asked, rarity=None):
        """从候选疾病涉及的、尚未问过的症状里挑分裂得分最高的作为下一问。
        rarity: {症状: 度中心性}，得分打平时优先问更"稀有"（中心性更低）的症状——
        稀有症状一锤定音的概率更大，能让候选集收窄得更快"""
        pool = set()
        for d in candidates:
            pool |= self.disease_symptoms[d]
        pool -= asked
        best, best_score = None, -1.0
        # 遍历顺序 = (度中心性, 症状名)：得分完全相同时排在前面的胜出，
        # 也就实现了"同分先问稀有症状"的平局裁决；得分不同时仍以得分为准
        for symptom in sorted(pool, key=lambda s: (rarity or {}).get(s, 0.0)):
            score = self.split_score(symptom, candidates)
            if score > best_score:
                best, best_score = symptom, score
        return best

    def split(self, symptom, candidates, answer):
        """按回答分裂候选集：yes 保留有该症状的疾病，no 保留没有的，unknown 不分裂"""
        if answer == "yes":
            return {d for d in candidates if symptom in self.disease_symptoms[d]}
        if answer == "no":
            return {d for d in candidates if symptom not in self.disease_symptoms[d]}
        return set(candidates)
