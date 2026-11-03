# -*- coding: utf-8 -*-
"""
knowledge_base.py —— 医疗专家系统知识库
在基础实训代码（6 条规则、8 个症状）的基础上扩充为：
  - 12 种常见疾病，33 个症状，症状带权重（3=典型症状，2=常见症状，1=非特异症状）
  - 每种疾病配有推荐检查、就诊科室、处置建议、注意事项、常用药物参考、并发症
  - 3 条急诊红旗规则 + 1 条脱水预警规则
  - 症状按身体区域分组，供 GUI 分组展示
  - 并发症关系构成"疾病→并发症"有向图，供推理引擎做传递闭包（多级风险预警）
说明：本知识库内容仅用于离散数学课程实训，不构成真实医疗建议。
"""

# ---------------- 疾病规则库 ----------------
# symptoms: {症状名: 权重}，权重衡量该症状对本疾病的"典型程度"
DISEASES = {
    "流行性感冒": {
        "symptoms": {"发热": 3, "肌肉酸痛": 3, "咳嗽": 2, "头痛": 2, "乏力": 2,
                     "喉咙痛": 2, "鼻塞": 1},
        "tests": ["流感病毒抗原检测", "血常规"],
        "department": "呼吸内科 / 感染科",
        "advice": "居家隔离休息，多饮水，监测体温；高热不退或呼吸困难及时就医",
        "note": "发病 48 小时内就医可考虑抗病毒治疗",
        "medications": ["对乙酰氨基酚（退热，遵医嘱）"],
        "complications": ["病毒性肺炎", "心肌炎"],
        "urgency": "common",
    },
    "普通感冒": {
        "symptoms": {"鼻塞": 3, "流鼻涕": 3, "打喷嚏": 2, "喉咙痛": 2,
                     "乏力": 1, "头痛": 1, "发热": 1},
        "exclude": {"呼吸困难": -2},
        "tests": ["一般无需检查，症状加重时查血常规"],
        "department": "呼吸内科",
        "advice": "多休息、多饮水，一般 5~7 天自愈",
        "note": "若发热超过 3 天或出现胸闷，需就医排除下呼吸道感染",
        "medications": ["复方感冒药（按说明书使用）"],
        "complications": ["鼻窦炎"],
        "urgency": "common",
    },
    "肺炎": {
        "symptoms": {"发热": 3, "咳嗽": 3, "咳痰": 2, "呼吸困难": 3, "胸痛": 2, "乏力": 1,
                     "咯血": 1, "意识模糊": 1},
        "tests": ["胸部X光/CT", "血常规", "CRP"],
        "department": "呼吸内科",
        "advice": "尽快就医，明确病原体后规范抗感染治疗",
        "note": "老人、儿童及慢病患者病情变化快，建议尽早就诊",
        "medications": ["抗感染药物需医生处方，勿自行服用"],
        "complications": ["脓胸", "呼吸衰竭"],
        "urgency": "serious",
    },
    "急性支气管炎": {
        "symptoms": {"咳嗽": 3, "咳痰": 3, "胸闷": 2, "发热": 1, "喉咙痛": 1},
        "tests": ["胸部X光", "血常规"],
        "department": "呼吸内科",
        "advice": "休息、多饮水，避免烟雾刺激；咳嗽超过 3 周需复诊",
        "note": "与肺炎的鉴别要点是呼吸困难和胸痛程度",
        "medications": ["止咳化痰类药品（遵医嘱）"],
        "complications": ["肺炎"],
        "urgency": "common",
    },
    "偏头痛": {
        "symptoms": {"头痛": 3, "畏光": 3, "恶心": 2, "呕吐": 1, "眩晕": 1},
        "tests": ["神经系统查体", "必要时头颅CT/MRI"],
        "department": "神经内科",
        "advice": "在安静避光的房间休息，记录头痛日记寻找诱因",
        "note": "突发剧烈头痛或伴意识改变需立即急诊",
        "medications": ["急性发作药物需医生评估后使用"],
        "complications": ["慢性偏头痛"],
        "urgency": "common",
    },
    "紧张性头痛": {
        "symptoms": {"头痛": 3, "颈肩酸痛": 3, "失眠": 2, "乏力": 1, "注意力不集中": 1},
        "exclude": {"畏光": -2},
        "tests": ["一般无需检查，必要时查颈椎片"],
        "department": "神经内科",
        "advice": "规律作息，放松颈肩部，适度运动",
        "note": "与偏头痛的鉴别：本类型多为双侧紧箍感、无畏光畏声",
        "medications": ["必要时短期使用常规镇痛药（遵医嘱）"],
        "complications": ["慢性紧张性头痛"],
        "urgency": "common",
    },
    "急性胃肠炎": {
        "symptoms": {"腹痛": 3, "腹泻": 3, "恶心": 2, "呕吐": 2, "发热": 1},
        "tests": ["血常规", "粪便常规"],
        "department": "消化内科",
        "advice": "清淡饮食，少量多次补液，注意手部卫生",
        "note": "出现持续高热、血便或明显脱水需就医",
        "medications": ["口服补液盐", "蒙脱石散（遵医嘱）"],
        "complications": ["脱水", "电解质紊乱"],
        "urgency": "common",
    },
    "食物中毒": {
        "symptoms": {"呕吐": 3, "腹泻": 3, "腹痛": 2, "发热": 1, "食用可疑食物史": 3},
        "tests": ["粪便常规", "必要时毒物检测"],
        "department": "急诊 / 消化内科",
        "advice": "立即停止进食可疑食物，保留样本；集体发病应同时上报",
        "note": "呕吐腹泻严重时尽快就医，防止脱水",
        "medications": ["不要自行止泻，及时就医"],
        "complications": ["脱水"],
        "urgency": "serious",
    },
    "过敏性鼻炎": {
        "symptoms": {"打喷嚏": 3, "流鼻涕": 3, "鼻塞": 2, "眼睛痒": 3},
        "exclude": {"发热": -2},
        "tests": ["过敏原检测"],
        "department": "耳鼻喉科 / 变态反应科",
        "advice": "远离过敏原，花粉季节外出戴口罩",
        "note": "症状与感冒相似，但通常不发热且接触过敏原后发作",
        "medications": ["抗组胺药（遵医嘱）"],
        "complications": ["鼻窦炎", "哮喘"],
        "urgency": "common",
    },
    "急性咽炎": {
        "symptoms": {"喉咙痛": 3, "吞咽困难": 2, "发热": 2, "声音嘶哑": 1, "咳嗽": 1},
        "tests": ["咽部查体", "血常规"],
        "department": "耳鼻喉科",
        "advice": "温凉流质饮食，淡盐水漱口，少说话",
        "note": "张口困难或呼吸不畅提示脓肿形成，需急诊",
        "medications": ["含片缓解症状（遵医嘱）"],
        "complications": ["扁桃体周围脓肿"],
        "urgency": "common",
    },
    "尿路感染": {
        "symptoms": {"尿频": 3, "尿急": 3, "尿痛": 3, "发热": 1, "腰痛": 1},
        "tests": ["尿常规", "尿培养"],
        "department": "泌尿外科 / 肾内科",
        "advice": "多饮水增加排尿，勿憋尿，注意个人卫生",
        "note": "出现高热腰痛提示上尿路感染，需及时治疗",
        "medications": ["抗菌药物需医生处方"],
        "complications": ["肾盂肾炎"],
        "urgency": "common",
    },
    "新型冠状病毒感染": {
        "symptoms": {"发热": 2, "咳嗽": 2, "乏力": 2, "味觉减退": 3, "嗅觉减退": 3,
                     "喉咙痛": 1, "呼吸困难": 1},
        "tests": ["新冠抗原/核酸检测", "血常规"],
        "department": "感染科 / 发热门诊",
        "advice": "居家休息，监测血氧，出现胸闷气促立即就医",
        "note": "老年人及基础病患者重点监测血氧饱和度",
        "medications": ["对症用药，遵医嘱"],
        "complications": ["病毒性肺炎"],
        "urgency": "common",
    },
}

# ---------------- 排除症状说明 ----------------
# exclude: {症状: 负权重}。出现该症状时对置信度做扣减——它提示"这个病不太像"。
# 三条都是教科书级鉴别点：过敏性鼻炎通常不发热；普通感冒不应有呼吸困难
# （出现则提示向下呼吸道进展）；紧张性头痛无畏光（畏光提示偏头痛）。

# ---------------- 急诊红旗规则 ----------------
# match 为 "any" 表示出现任一症状即触发，"all" 表示全部出现才触发
RED_FLAGS = [
    {"symptoms": {"咯血"}, "match": "any",
     "message": "出现咯血，可能提示肺部严重疾病，请立即急诊！", "level": "emergency"},
    {"symptoms": {"意识模糊"}, "match": "any",
     "message": "出现意识模糊，可能提示中枢神经系统受累，请立即急诊！", "level": "emergency"},
    {"symptoms": {"呼吸困难"}, "match": "any",
     "message": "出现呼吸困难，警惕重症肺炎等疾病，请尽快急诊！", "level": "emergency"},
    {"symptoms": {"呕吐", "腹泻"}, "match": "all",
     "message": "呕吐与腹泻同时出现，注意脱水风险，建议及时补液并就医。", "level": "warning"},
]

# ---------------- 并发症有向图的补充边 ----------------
# DISEASES 中已含"疾病→并发症"的一级边，这里补充"并发症→更远并发症"的边，
# 两者合并后构成完整有向图，供传递闭包推导多级风险链（如 胃肠炎→脱水→电解质紊乱）
EXTRA_COMPLICATION_EDGES = [
    ("病毒性肺炎", "呼吸衰竭"),
    ("脱水", "电解质紊乱"),
    ("肾盂肾炎", "败血症"),
]

# ---------------- 症状分组（GUI 展示用） ----------------
SYMPTOM_GROUPS = {
    "全身症状": ["发热", "乏力", "肌肉酸痛", "头痛", "意识模糊", "咯血"],
    "呼吸系统": ["咳嗽", "咳痰", "呼吸困难", "胸痛", "胸闷", "喉咙痛",
                 "声音嘶哑", "吞咽困难"],
    "头颈部": ["鼻塞", "流鼻涕", "打喷嚏", "眼睛痒", "畏光", "眩晕",
               "颈肩酸痛", "失眠", "注意力不集中", "味觉减退", "嗅觉减退"],
    "消化系统": ["腹痛", "腹泻", "恶心", "呕吐", "食用可疑食物史"],
    "泌尿系统": ["尿频", "尿急", "尿痛", "腰痛"],
}

# 智能问诊时把症状名转成自然问句（没有配置的症状直接问"是否XX"）
SYMPTOM_QUESTIONS = {
    "发热": "最近是否发热（体温 ≥ 37.3℃）？",
    "咯血": "是否出现过咳血或痰中带血？",
    "味觉减退": "最近味觉是否明显减退？",
    "嗅觉减退": "最近嗅觉是否明显减退？",
    "吞咽困难": "吞咽时是否疼痛或困难？",
    "食用可疑食物史": "近期是否吃过变质/可疑食物，或同食者多人同时发病？",
    "畏光": "看光亮时是否明显不适（畏光）？",
    "尿痛": "排尿时是否有疼痛或灼热感？",
    "注意力不集中": "最近是否注意力难以集中？",
}

DISCLAIMER = ("本系统为离散数学课程实训作品，结果仅供参考，"
              "不能替代执业医师的诊断，如有不适请及时就医。")


def get_all_symptoms():
    """从规则库中提取全部症状的有序列表（集合的并运算）"""
    symptoms = set()
    for info in DISEASES.values():
        symptoms.update(info["symptoms"])
    return sorted(symptoms)


def symptom_question(symptom):
    """返回症状对应的问诊问句"""
    return SYMPTOM_QUESTIONS.get(symptom, f"是否出现「{symptom}」？")


def build_complication_edges():
    """汇总所有"疾病→并发症"有向边，返回 (起点, 终点) 列表"""
    edges = []
    for disease, info in DISEASES.items():
        for comp in info["complications"]:
            edges.append((disease, comp))
    edges.extend(EXTRA_COMPLICATION_EDGES)
    return edges


# 知识库自检：症状分组必须覆盖全部症状且组间不重复
def _self_check():
    grouped = [s for members in SYMPTOM_GROUPS.values() for s in members]
    assert len(grouped) == len(set(grouped)), "症状分组内存在重复症状"
    all_symptoms = set(get_all_symptoms())
    # 红旗规则里的症状也必须在分组中出现，否则界面上选不到
    for flag in RED_FLAGS:
        for s in flag["symptoms"]:
            assert s in all_symptoms, f"红旗症状 {s} 不在任何疾病规则中"
    # 排除症状必须是全局症状空间里的合法症状，且不能与本病症状自相矛盾
    for d, info in DISEASES.items():
        for s in info.get("exclude", {}):
            assert s in all_symptoms, f"{d} 的排除症状 {s} 不在症状空间中"
            assert s not in info["symptoms"], f"{d} 同时包含和排除 {s}"


_self_check()
