import streamlit as st
from PIL import Image

st.set_page_config(page_title="VendaIA", page_icon="🛍️", layout="wide")
st.title("🛍️ VendaIA")
st.caption("Transforme uma foto do produto em conteúdo pronto para vender.")
st.divider()

left, right = st.columns([1, 1.2])
with left:
    st.subheader("📸 Seu produto")
    uploaded = st.file_uploader("Envie uma foto", type=["png","jpg","jpeg","webp"])
    product_name = st.text_input("Nome do produto", placeholder="Ex.: Camisa masculina")
    audience = st.text_input("Público-alvo", placeholder="Ex.: homens de 18 a 35 anos")
    style = st.selectbox("Estilo do anúncio", ["Profissional","Casual","Premium","UGC","Direto para venda"])
    if uploaded:
        st.image(Image.open(uploaded), caption="Produto enviado", use_container_width=True)
    generate = st.button("✨ Gerar conteúdo", type="primary", use_container_width=True)

def content(name, audience):
    name=name.strip() or "Produto"
    audience=audience.strip() or "clientes interessados"
    return {
        "Título": f"{name} — qualidade, estilo e praticidade",
        "Descrição": f"Conheça o {name}, pensado para {audience}. Uma opção versátil para quem procura qualidade, praticidade e um ótimo visual.",
        "Anúncio": f"🔥 Conheça o {name}! Uma opção para {audience} que busca qualidade e praticidade. Confira os detalhes e descubra esse produto.",
        "Instagram": f"✨ Seu próximo favorito pode estar aqui: {name}. Qualidade, estilo e praticidade em um só produto. Salve e compartilhe!",
        "UGC 20s": f"[0–3s] Mostre o produto: “Gente, olha isso aqui!”\n[3–8s] Mostre detalhes do {name}.\n[8–15s] Mostre o produto em uso e destaque seus benefícios.\n[15–20s] Close final: “Vale conferir!”",
        "Hashtags": "#produto #oferta #comprasonline #achadinhos #lojaonline #novidade"
    }

if generate:
    if not uploaded:
        st.warning("Envie uma foto do produto antes de gerar.")
    else:
        st.session_state.content=content(product_name,audience)

with right:
    st.subheader("✨ Conteúdo gerado")
    if "content" not in st.session_state:
        st.info("Envie uma foto e toque em “Gerar conteúdo”.")
    else:
        for k,v in st.session_state.content.items():
            st.markdown(f"### {k}")
            st.text_area(k,v,height=100 if k!="UGC 20s" else 180,key="out_"+k)

st.divider()
st.caption("VendaIA V1 — protótipo. A próxima versão poderá analisar automaticamente a imagem com IA.")
