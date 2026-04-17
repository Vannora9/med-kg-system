import streamlit as st
import networkx as nx
import graphviz

st.set_page_config(page_title="中西医知识图谱对比系统", layout="wide")

# ==========================================
# 1. 模拟 LLM 信息抽取后的结构化数据
# （实际应用中，这里的数据由 LLM 提示词自动从文献解析为 JSON）
# ==========================================
data_western = {
    "disease": "感冒 (Common Cold)",
    "symptoms": ["发热", "头痛", "流涕", "咽痛"],
    "treatments": [
        {"drug": "布洛芬 (Ibuprofen)", "effect": "退热镇痛", "target": "发热, 头痛"},
        {"drug": "伪麻黄碱", "effect": "缓解鼻塞", "target": "流涕"}
    ]
}

data_tcm = {
    "disease": "感冒 (风寒表证)",
    "symptoms": ["恶寒重发热轻", "头痛无汗", "鼻塞流清涕", "脉浮紧"],
    "treatments": [
        {"drug": "荆防败毒散", "effect": "辛温解表，疏风散寒", "target": "恶寒重发热轻, 头痛无汗"},
        {"drug": "麻黄汤", "effect": "发汗解表，宣肺平喘", "target": "头痛无汗"}
    ]
}

# ==========================================
# 2. 构建知识图谱 (NetworkX -> Graphviz)
# ==========================================
def build_graph(data, system_name, color_scheme):
    dot = graphviz.Digraph(engine='dot')
    dot.attr(rankdir='LR', size='8,5')
    
    # 核心疾病节点
    disease_node = data["disease"]
    dot.node(disease_node, disease_node, shape='ellipse', style='filled', color=color_scheme['disease'])
    
    # 添加症状节点及关系
    for sym in data["symptoms"]:
        dot.node(sym, sym, shape='box', style='filled', color=color_scheme['symptom'])
        dot.edge(disease_node, sym, label="具有症状")
        
    # 添加药物、疗效及对应关系
    for treat in data["treatments"]:
        drug = treat["drug"]
        effect = treat["effect"]
        targets = treat["target"].split(", ")
        
        dot.node(drug, drug, shape='hexagon', style='filled', color=color_scheme['drug'])
        dot.node(effect, effect, shape='parallelogram', style='filled', color=color_scheme['effect'])
        
        dot.edge(drug, disease_node, label="治疗")
        dot.edge(drug, effect, label="具有疗效")
        
        for target in targets:
            if target in data["symptoms"]:
                dot.edge(drug, target, label="缓解/针对")
                
    return dot

# 配色方案
color_w = {'disease': '#FF9999', 'symptom': '#FFCC99', 'drug': '#99CCFF', 'effect': '#CCFFCC'}
color_t = {'disease': '#FF9999', 'symptom': '#FFCC99', 'drug': '#DDA0DD', 'effect': '#CCFFCC'}

# ==========================================
# 3. 前端界面与对比逻辑
# ==========================================
st.title("🌿 中西医诊疗知识图谱对比系统 (MVP)")
st.write("输入常见疾病，对比中西医在症状认知与用药治疗上的差异。")

disease_query = st.text_input("请输入疾病名称查询 (例如: 感冒)", "感冒")

if disease_query == "感冒":
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💊 西医知识图谱")
        st.write("**核心逻辑:** 针对具体症状（靶点）进行对症治疗（如抑制前列腺素合成退热）。")
        graph_w = build_graph(data_western, "西医", color_w)
        st.graphviz_chart(graph_w)
        
    with col2:
        st.subheader("🍵 中医知识图谱")
        st.write("**核心逻辑:** 辨证论治，关注整体状态（如风寒束表），通过发汗解表恢复阴阳平衡。")
        graph_t = build_graph(data_tcm, "中医", color_t)
        st.graphviz_chart(graph_t)
        
    st.divider()
    
    # ==========================================
    # 4. 自动知识融合与实体对齐引擎
    # ==========================================
    st.subheader("🤖 自动化实体对齐与对比分析")
    
    import difflib

    # 1. 模拟一个微型的医学本体字典 (Ontology Mapping)
    # 在实际应用中，这里可以替换为 LLM 实时判断或知识库查询
    medical_ontology = {
        "发热": ["发热轻", "发热重", "恶寒重发热轻", "壮热"],
        "流涕": ["流清涕", "鼻塞流清涕", "流浊涕"],
        "鼻塞": ["鼻塞流清涕"]
    }

    def calculate_similarity(s1, s2):
        """计算两个字符串的字面相似度"""
        return difflib.SequenceMatcher(None, s1, s2).ratio()

    def auto_align_symptoms(western_syms, tcm_syms):
        exact_matches = []
        ontology_matches = []
        fuzzy_matches = []
        unmatched_w = list(western_syms)
        unmatched_t = list(tcm_syms)

        # A. 绝对对齐 (Exact Match)
        for w in western_syms:
            if w in unmatched_t:
                exact_matches.append(w)
                unmatched_w.remove(w)
                unmatched_t.remove(w)

        # B. 本体字典对齐 (Ontology Mapping)
        for w in list(unmatched_w):
            if w in medical_ontology:
                for t in list(unmatched_t):
                    if t in medical_ontology[w]:
                        ontology_matches.append((w, t))
                        unmatched_w.remove(w)
                        unmatched_t.remove(t)
                        break # 假设一对一映射，找到即跳出

        # C. 模糊/语义对齐 (Fuzzy Match - 相似度阈值设为 0.4)
        for w in list(unmatched_w):
            for t in list(unmatched_t):
                if calculate_similarity(w, t) > 0.4:
                    fuzzy_matches.append((w, t, round(calculate_similarity(w, t), 2)))
                    unmatched_w.remove(w)
                    unmatched_t.remove(t)
                    break

        return exact_matches, ontology_matches, fuzzy_matches, unmatched_w, unmatched_t

    # 运行自动对齐算法
    exact, ontology, fuzzy, unique_w, unique_t = auto_align_symptoms(data_western["symptoms"], data_tcm["symptoms"])

    # 动态渲染分析结果
    col_res1, col_res2 = st.columns(2)
    
    with col_res1:
        st.markdown("#### 🔗 症状对齐结果 (Entity Alignment)")
        if exact:
            st.success(f"**绝对匹配:** {', '.join(exact)}")
        if ontology:
            for w, t in ontology:
                st.info(f"**本体映射:** [{w}] ↔ [{t}]")
        if fuzzy:
            for w, t, score in fuzzy:
                st.warning(f"**模糊匹配:** [{w}] ≈ [{t}] (相似度: {score})")
                
    with col_res2:
        st.markdown("#### ⚠️ 特异性症状 (Unmatched Entities)")
        st.write("**西医独有:**", ", ".join(unique_w) if unique_w else "无")
        st.write("**中医独有:**", ", ".join(unique_t) if unique_t else "无")

    # 动态生成治疗逻辑总结
    st.markdown("#### 💡 自动策略推导")
    st.write(f"在 {disease_query} 的治疗中，西医倾向于针对靶点（如：**{', '.join([t['target'] for t in data_western['treatments']])}**）进行直接干预。而中医不仅关注重叠症状，还处理了其特有表征（如：**{', '.join(unique_t)}**），采用的药物通常具有更复合的疗效（如：**{', '.join([t['effect'] for t in data_tcm['treatments']])}**）。")