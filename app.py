import streamlit as st
import networkx as nx
import graphviz
import difflib
import json
from openai import OpenAI

st.set_page_config(page_title="中西医知识图谱系统", layout="wide")

# ==========================================
# 0. 全局配置与预置数据
# ==========================================
# ⚠️ 注意：请用你新生成的 API Key 替换这里！
API_KEY = "ddbf62ed74dc4a0496f6531e262746f9.MN3UvFnKc48u9aO8" 
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/" 
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

color_w = {'disease': '#FF9999', 'symptom': '#FFCC99', 'drug': '#99CCFF', 'effect': '#CCFFCC'}
color_t = {'disease': '#FF9999', 'symptom': '#FFCC99', 'drug': '#DDA0DD', 'effect': '#CCFFCC'}

# 初始化一个全局的医学数据库到 Session State 中，这样大模型抽取的新数据也能存进来
if "medical_db" not in st.session_state:
    st.session_state.medical_db = {
        "感冒": {
            "w_data": {
                "disease": "感冒",
                "symptoms": ["发热", "头痛", "流涕", "咽痛"],
                "treatments": [
                    {"drug": "布洛芬", "effect": "退热镇痛", "target": "发热, 头痛"},
                    {"drug": "伪麻黄碱", "effect": "缓解鼻塞", "target": "流涕"}
                ]
            },
            "t_data": {
                "disease": "风寒感冒",
                "symptoms": ["恶寒重发热轻", "头痛无汗", "鼻塞流清涕", "脉浮紧"],
                "treatments": [
                    {"drug": "荆防败毒散", "effect": "辛温解表", "target": "恶寒重发热轻, 头痛无汗"},
                    {"drug": "麻黄汤", "effect": "发汗解表", "target": "头痛无汗"}
                ]
            },
            "search_index": set(["发热", "头痛", "流涕", "咽痛", "恶寒重发热轻", "头痛无汗", "鼻塞流清涕", "脉浮紧"])
        },
        "偏头痛": {
            "w_data": {
                "disease": "偏头痛",
                "symptoms": ["头痛", "恶心", "畏光", "搏动性疼痛"],
                "treatments": [{"drug": "布洛芬", "effect": "镇痛", "target": "头痛"}]
            },
            "t_data": {
                "disease": "偏头痛 (肝阳上亢)",
                "symptoms": ["头痛", "眩晕", "心烦易怒", "脉弦"],
                "treatments": [{"drug": "天麻钩藤饮", "effect": "平肝潜阳", "target": "头痛, 眩晕, 心烦易怒"}]
            },
            "search_index": set(["头痛", "恶心", "畏光", "搏动性疼痛", "眩晕", "心烦易怒", "脉弦"])
        }
    }

# ==========================================
# 1. 核心功能函数定义
# ==========================================
def extract_kg_from_text(text, system_type):
    system_prompt = f"""
    你是一个专业的医学实体关系抽取专家。请阅读提供的{system_type}医学文本，提取疾病名称、症状、以及治疗药物和疗效。
    必须严格输出合法的 JSON 格式。
    {{
        "disease": "疾病名称(如感冒)",
        "symptoms": ["症状1", "症状2"],
        "treatments": [
            {{"drug": "药物名称", "effect": "药物疗效", "target": "针对的症状(必须从symptoms中选)"}}
        ]
    }}
    """
    try:
        response = client.chat.completions.create(
            model="glm-4-flash", # 修复：改回智谱的模型名称
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        raw_output = response.choices[0].message.content
        # 清理可能出现的 markdown 标记
        raw_output = raw_output.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_output)
    except Exception as e:
        st.error(f"{system_type}知识抽取失败: {e}")
        return None

def build_graph(data, system_name, color_scheme):
    dot = graphviz.Digraph(engine='dot')
    dot.attr(rankdir='LR', size='8,5')
    
    # 终极防御 1：防止 data 本身解析失败变成 None
    if not isinstance(data, dict):
        return dot
        
    disease_node = str(data.get("disease", "未知疾病"))
    dot.node(disease_node, disease_node, shape='ellipse', style='filled', color=color_scheme['disease'])
    
    # 终极防御 2：确保 symptoms 是个列表
    symptoms = data.get("symptoms", [])
    if isinstance(symptoms, list):
        for sym in symptoms:
            sym_str = str(sym)
            dot.node(sym_str, sym_str, shape='box', style='filled', color=color_scheme['symptom'])
            dot.edge(disease_node, sym_str, label="具有症状")
    else:
        symptoms = []
            
    # 终极防御 3：处理 treatments 里的各种花式错乱格式
    treatments = data.get("treatments", [])
    if isinstance(treatments, list):
        for treat in treatments:
            if isinstance(treat, dict):
                drug = str(treat.get("drug", "未知药物"))
                effect = str(treat.get("effect", "未知疗效"))
                
                # 核心修复区：处理 target 是 null、列表、或字符串的情况
                raw_target = treat.get("target")
                if isinstance(raw_target, str):
                    # 如果是字符串，按逗号拆分并去掉空格
                    targets = [t.strip() for t in raw_target.split(",") if t.strip()]
                elif isinstance(raw_target, list):
                    # 如果大模型直接输出了列表，直接转成字符串列表
                    targets = [str(t) for t in raw_target]
                else:
                    # 如果是 null 或者其他乱七八糟的东西，设为空列表
                    targets = []
                    
            elif isinstance(treat, str):
                drug = treat
                effect = "未提取出疗效"
                targets = []
            else:
                continue
                
            dot.node(drug, drug, shape='hexagon', style='filled', color=color_scheme['drug'])
            dot.node(effect, effect, shape='parallelogram', style='filled', color=color_scheme['effect'])
            
            dot.edge(drug, disease_node, label="治疗")
            dot.edge(drug, effect, label="具有疗效")
            
            for target in targets:
                if target and target in symptoms:
                    dot.edge(drug, target, label="缓解/针对")
                    
    return dot

def auto_align_symptoms(western_syms, tcm_syms):
    medical_ontology = {
        "发热": ["发热轻", "发热重", "恶寒重发热轻", "壮热"],
        "流涕": ["流清涕", "鼻塞流清涕", "流浊涕"],
        "鼻塞": ["鼻塞流清涕"]
    }
    
    exact_matches, ontology_matches, fuzzy_matches = [], [], []
    unmatched_w = list(western_syms)
    unmatched_t = list(tcm_syms)

    for w in western_syms:
        if w in unmatched_t:
            exact_matches.append(w)
            unmatched_w.remove(w)
            unmatched_t.remove(w)

    for w in list(unmatched_w):
        if w in medical_ontology:
            for t in list(unmatched_t):
                if t in medical_ontology[w]:
                    ontology_matches.append((w, t))
                    unmatched_w.remove(w)
                    unmatched_t.remove(t)
                    break 

    for w in list(unmatched_w):
        for t in list(unmatched_t):
            score = difflib.SequenceMatcher(None, w, t).ratio()
            if score > 0.4:
                fuzzy_matches.append((w, t, round(score, 2)))
                unmatched_w.remove(w)
                unmatched_t.remove(t)
                break

    return exact_matches, ontology_matches, fuzzy_matches, unmatched_w, unmatched_t

def render_kg_comparison(data_western, data_tcm, title_prefix=""):
    """封装好的图谱渲染与对比模块"""
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💊 西医知识图谱")
        st.graphviz_chart(build_graph(data_western, "西医", color_w))
    with col2:
        st.subheader("🍵 中医知识图谱")
        st.graphviz_chart(build_graph(data_tcm, "中医", color_t))
        
    st.divider()
    st.subheader(f"🤖 自动化实体对齐与对比分析 {title_prefix}")
    
    exact, ontology, fuzzy, unique_w, unique_t = auto_align_symptoms(data_western["symptoms"], data_tcm["symptoms"])

    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.markdown("#### 🔗 症状对齐结果")
        if exact: st.success(f"**绝对匹配:** {', '.join(exact)}")
        if ontology:
            for w, t in ontology: st.info(f"**本体映射:** [{w}] ↔ [{t}]")
        if fuzzy:
            for w, t, score in fuzzy: st.warning(f"**模糊匹配:** [{w}] ≈ [{t}] (相似度: {score})")
                
    with col_res2:
        st.markdown("#### ⚠️ 特异性症状")
        st.write("**西医独有:**", ", ".join(unique_w) if unique_w else "无")
        st.write("**中医独有:**", ", ".join(unique_t) if unique_t else "无")

# ==========================================
# 2. UI 界面组装
# ==========================================
st.title("🌿 中西医诊疗知识图谱构建与对比系统")

tab_extract, tab_search = st.tabs(["⚙️ 自动文献抽取", "🔍 知识图谱检索 (含症状推演)"])

# ----------------- Tab 1: 自动抽取 -----------------
with tab_extract:
    st.markdown("### 📚 输入医学文献进行自动化抽取")
    col_text1, col_text2 = st.columns(2)
    with col_text1:
        western_text = st.text_area("粘贴西医文献/指南:", height=150)
    with col_text2:
        tcm_text = st.text_area("粘贴中医文献/典籍:", height=150)

    if st.button("🚀 一键构建知识图谱并存入数据库", type="primary"):
        if western_text and tcm_text:
            with st.spinner("大模型正在疯狂阅读并提取实体关系..."):
                w_kg = extract_kg_from_text(western_text, "现代医学")
                t_kg = extract_kg_from_text(tcm_text, "传统中医学")
                
                if w_kg and t_kg:
                    # 提取成功，动态更新到全局数据库中！
                    new_disease_name = w_kg.get("disease", "未知疾病")
                    new_index = set(w_kg.get("symptoms", []) + t_kg.get("symptoms", []))
                    
                    st.session_state.medical_db[new_disease_name] = {
                        "w_data": w_kg,
                        "t_data": t_kg,
                        "search_index": new_index
                    }
                    st.success(f"🎉 成功构建【{new_disease_name}】的知识图谱并入库！可以在右侧标签页搜索体验。")
                    
                    # 立即渲染刚刚抽取的图谱
                    render_kg_comparison(w_kg, t_kg, title_prefix=f"({new_disease_name})")
        else:
            st.warning("请同时输入中西医的文献文本。")

# ----------------- Tab 2: 检索与推演 -----------------
with tab_search:
    db = st.session_state.medical_db
    
    sub_tab1, sub_tab2 = st.tabs(["🩺 按疾病精确查询", "🔍 按症状智能推演"])
    
    with sub_tab1:
        disease_query = st.selectbox("请选择要查看的疾病图谱:", list(db.keys()))
        if disease_query:
            render_kg_comparison(db[disease_query]["w_data"], db[disease_query]["t_data"])
            
    with sub_tab2:
        all_symptoms = set()
        for d_info in db.values():
            all_symptoms.update(d_info["search_index"])
            
        selected_symptoms = st.multiselect("选择患者出现的症状，系统将自动推演:", list(all_symptoms))
        
        if selected_symptoms:
            match_results = []
            user_sym_set = set(selected_symptoms)
            
            for disease_name, info in db.items():
                overlap = user_sym_set.intersection(info["search_index"])
                if overlap:
                    match_results.append({
                        "disease": disease_name,
                        "score": len(overlap),
                        "matched_syms": list(overlap)
                    })
            
            match_results.sort(key=lambda x: x["score"], reverse=True)
            
            if match_results:
                for res in match_results:
                    with st.expander(f"📌 {res['disease']} (匹配度: {res['score']} 项 - {', '.join(res['matched_syms'])})"):
                        # 这里为了简洁只展示图谱，不展示对比分析文字
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.graphviz_chart(build_graph(db[res['disease']]['w_data'], "西医", color_w))
                        with col_b:
                            st.graphviz_chart(build_graph(db[res['disease']]['t_data'], "中医", color_t))
            else:
                st.info("没有匹配到相关疾病。")