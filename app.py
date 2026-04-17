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
    
    # 对比分析引擎 (模拟)
    st.subheader("🔍 智能对比分析")
    
    # 模拟简单的求交集/差集逻辑
    western_sym = set(data_western["symptoms"])
    tcm_sym = set(data_tcm["symptoms"])
    
    st.markdown("#### 1. 症状认知对比")
    st.write("- **相似点:** 两者都关注到了体温异常（发热 vs 恶寒发热）、头部不适（头痛）和呼吸道症状（流涕）。")
    st.write("- **差异点:** 中医图谱额外引入了体征观察（**脉浮紧**）以及对冷热的主观感受细分（**恶寒重发热轻**），而西医图谱更倾向于客观症状的平铺。")
    
    st.markdown("#### 2. 治疗策略对比")
    st.write("- **西医用药:** 呈现明显的 **多对一** 靶向特征，布洛芬直击发热和头痛，伪麻黄碱直击流涕。")
    st.write("- **中医用药:** 呈现 **系统性** 特征，荆防败毒散同时作用于多个症状（恶寒、发热、头痛），其疗效（辛温解表）是针对疾病的病机（风寒），而非单一症状。")

else:
    st.info("目前MVP版本仅录入了「感冒」的数据，请尝试输入「感冒」。")