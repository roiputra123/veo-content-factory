import streamlit as st
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.prompt_engine.niche_loader import NicheLoader

st.set_page_config(page_title="Veo Content Factory", layout="wide", page_icon="🎬")

st.title("🎬 Veo Content Factory")
st.markdown("---")

niche_loader = NicheLoader()
niches = niche_loader.list_niche_names()

if "step" not in st.session_state:
    st.session_state.step = 1
if "niche" not in st.session_state:
    st.session_state.niche = None
if "idea" not in st.session_state:
    st.session_state.idea = ""
if "prompt_result" not in st.session_state:
    st.session_state.prompt_result = None

# --- STEP 1: PILIH NICHE ---
if st.session_state.step == 1:
    st.markdown("## Pilih Tipe Video")
    cols = st.columns(2)
    for i, n in enumerate(niches):
        with cols[i % 2]:
            if st.button(f"**{n['name']}**\n{n['description']}", use_container_width=True):
                st.session_state.niche = n["slug"]
                st.session_state.step = 2
                st.rerun()

# --- STEP 2: INPUT IDE ---
elif st.session_state.step == 2:
    st.markdown(f"## {niche_loader.load(st.session_state.niche)['name']}")
    st.markdown("---")
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("### Ide / Kata Kunci")
        idea = st.text_area(
            "Deskripsikan video yang kamu inginkan",
            placeholder="Contoh: rumah mewah modern 2 lantai dengan kolam renang, taman minimalis, dan interior marmer",
            height=120,
        )
        st.markdown("### Opsi Tambahan")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            duration = st.selectbox("Durasi", [5, 8, 15], index=1)
        with col_b:
            aspect = st.selectbox("Aspek Rasio", ["16:9", "9:16", "1:1"], index=0)
        with col_c:
            audio = st.selectbox("Audio", ["Ya", "Tidak"], index=0)
        ref_image = st.file_uploader("Referensi Gambar (opsional)", type=["png", "jpg", "jpeg"])
        st.markdown("---")
        if st.button("🚀 Generate Prompt", type="primary", use_container_width=True):
            st.session_state.idea = idea
            st.session_state.duration = duration
            st.session_state.aspect = aspect
            st.session_state.audio = audio
            st.session_state.ref_image = ref_image
            st.session_state.step = 3
            st.rerun()
    with col2:
        profile = niche_loader.load(st.session_state.niche)
        st.markdown("### Profile Niche")
        st.info(f"**Camera:** {profile.get('cinematography', {}).get('camera_default', '-')}")
        st.info(f"**Lighting:** {profile.get('context', {}).get('lighting_default', '-')}")
        st.info(f"**Style:** {profile.get('style', {}).get('visual', '-')}")

# --- STEP 3: HASIL PROMPT ---
elif st.session_state.step == 3:
    st.markdown("## Hasil Prompt")
    st.markdown("---")
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("### 5-Part Prompt")
        parts = {
            "🎥 Cinematography": "Low-angle crane shot starting close to foundation and slowly rising (thats where the camera is).",
            "🏠 Subject": "A modern luxury villa with clean geometric lines, large glass windows, and natural stone facade.",
            "🎬 Action": "Workers pouring concrete foundation, scaffolding rising around the structure, time-lapse speed.",
            "🌳 Context": "Empty lot in an upscale suburban development, golden hour sunset lighting, dust particles floating.",
            "🎨 Style & Audio": "Cinematic, hyper-realistic, architectural visualization. Audio: construction site ambience.",
        }
        for label, content in parts.items():
            with st.expander(label, expanded=True):
                st.markdown(content)
                if st.button(f"✏ Edit", key=label):
                    pass
        st.markdown("---")
        st.markdown("### ⛔ Negative Prompt")
        st.code("blurry, distorted, deformed, low quality, watermark, text overlay, subtitle, cartoon, unrealistic materials", language="text")
        col_i, col_g, col_s = st.columns(3)
        with col_i:
            st.button("↻ Iterate (LLM)", use_container_width=True)
        with col_g:
            st.button("💾 Simpan Template", use_container_width=True)
        with col_s:
            st.button("▶ Generate Video (Veo)", type="primary", use_container_width=True)
    with col2:
        st.markdown("### Skor & Feedback")
        st.markdown("#### ⭐ 7.2 / 10")
        st.progress(0.72)
        st.markdown("**Feedback:**")
        st.warning("- Lighting description too generic")
        st.warning("- Missing explicit camera lens specification")
        st.info("- Audio direction could be more specific")
        st.markdown("---")
        st.markdown("### Riwayat Iterasi")
        st.markdown("`Iter 1` ⭐ 5.2 → generik")
        st.markdown("`Iter 2` ⭐ 7.2 → improved camera")
        st.markdown("`Iter 3` ⭐ 8.8 → ✅ ready")
        if st.button("← Kembali ke Input", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
