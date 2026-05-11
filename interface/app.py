import streamlit as st
import sys
import os
import json
import tempfile

_BASE = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "app"))

from prompt_engine.niche_loader import NicheLoader
from prompt_engine.refiner import PromptRefiner
from core.logger import ProductionLogger

st.set_page_config(page_title="Veo Content Factory", layout="wide", page_icon="🎬")

st.title("🎬 Veo Content Factory")

with st.sidebar:
    st.markdown("### 🧭 Navigasi")
    if st.button("🏠 Beranda", use_container_width=True):
        st.session_state.step = 1
        st.session_state.niche = None
        st.session_state.idea = ""
        st.session_state.result = None
        st.rerun()
    step_now = st.session_state.get("step", 1)
    labels = {1: "Pilih Niche", 2: "Input Ide", 3: "Hasil Prompt", 4: "Generate Video"}
    for s, label in labels.items():
        mark = "▸" if s == step_now else " "
        st.markdown(f"{mark} **Langkah {s}:** {label}")

st.markdown("---")

if "step" not in st.session_state:
    st.session_state.step = 1
    st.session_state.niche = None
    st.session_state.idea = ""
    st.session_state.result = None
    st.session_state.log = []

niche_loader = NicheLoader()
niches = niche_loader.list_niche_names()

def log(msg):
    st.session_state.log.append(msg)

# --- LANGKAH 1: PILIH NICHE ---
if st.session_state.step == 1:
    st.markdown("## Pilih Tipe Video")
    st.caption("Pilih kategori yang paling sesuai dengan proyek Anda")
    cols = st.columns(2)
    for i, n in enumerate(niches):
        with cols[i % 2]:
            num = i + 1
            label = f"**{num}. {n['name']}**\n{n['description']}"
            if st.button(label, use_container_width=True, key=f"niche_{num}"):
                st.session_state.niche = n["slug"]
                st.session_state.step = 2
                st.rerun()

# --- LANGKAH 2: INPUT IDE ---
elif st.session_state.step == 2:
    profile = niche_loader.load(st.session_state.niche)
    st.markdown(f"## {profile['name']}")
    st.markdown("---")

    col1, col2 = st.columns([3, 2])

    with col1:
        idea = st.text_area(
            "Deskripsi Ide",
            placeholder="Contoh: rumah mewah modern 2 lantai, kolam renang, taman minimalis...",
            height=120,
        )

        dur = st.selectbox("Durasi (detik)", [5, 8, 15], index=1)
        aspect = st.selectbox("Rasio Layar", ["16:9", "9:16", "1:1"], index=0)
        audio = st.radio("Audio", ["Tidak", "Ya"], index=0, horizontal=True)
        ref_image = st.file_uploader("Gambar Referensi (opsional)", type=["png", "jpg", "jpeg"])

        st.markdown("---")
        if st.button("🚀 Buat Prompt", type="primary", use_container_width=True):
            if not idea.strip():
                st.error("Masukkan ide terlebih dahulu")
            else:
                st.session_state.idea = idea
                st.session_state.duration = dur
                st.session_state.aspect = aspect
                st.session_state.audio = audio
                st.session_state.ref_image = ref_image
                st.session_state.step = 3
                st.rerun()

    with col2:
        st.markdown("### Profile Niche")
        cam = profile.get("cinematography", {}).get("camera_default", "-")
        lighting = profile.get("context", {}).get("lighting_default", "-")
        visual = profile.get("style", {}).get("visual", "-")
        st.info(f"**Kamera:** {cam}")
        st.info(f"**Pencahayaan:** {lighting}")
        st.info(f"**Gaya Visual:** {visual}")
        with st.expander("Lihat Vocabulary"):
            st.json({
                "subjek": profile.get("subject", {}).get("vocabulary", []),
                "aksi": profile.get("action", {}).get("vocabulary", []),
            })
        st.markdown("---")
        if st.button("← Beranda", use_container_width=True):
            st.session_state.step = 1
            st.rerun()

# --- LANGKAH 3: HASIL PROMPT ---
elif st.session_state.step == 3:
    if st.session_state.result is None:
        with st.spinner("Memperhalus prompt dengan LLM..."):
            try:
                refiner = PromptRefiner(logger=ProductionLogger())
                img_path = None
                if st.session_state.ref_image:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                    tmp.write(st.session_state.ref_image.getvalue())
                    img_path = tmp.name

                result = refiner.refine_prompt(
                    user_input=st.session_state.idea,
                    niche_slug=st.session_state.niche,
                    image_path=img_path,
                )
                st.session_state.result = result
                log(f"✅ Prompt selesai — skor: {result.get('score', 'N/A')}/10")
            except Exception as e:
                st.error(f"Gagal: {e}")
                st.session_state.result = {"positive": "Error", "negative": "", "score": 0}

    result = st.session_state.result
    score = result.get("score", 0)

    st.markdown("## Hasil Prompt")

    col_score, col_iter = st.columns([1, 3])
    with col_score:
        val = score / 10 if score else 0
        st.markdown(f"### ⭐ {score}/10")
        st.progress(val)
        fb = result.get('iterations', [{}])[-1].get('feedback', '')
        st.caption(fb[:60])
    with col_iter:
        iters = result.get("iterations", [])
        if iters:
            st.markdown("**Riwayat Iterasi:**")
            for it in iters:
                s = it.get("score", 0)
                emoji = "✅" if s >= 9 else "↻" if s >= 7 else "✗"
                st.markdown(f"`Iter {it['iteration']}` {emoji} ⭐{s} — {it.get('feedback', '')[:40]}")

    st.markdown("---")
    col_p, col_n = st.columns(2)
    with col_p:
        st.markdown("### Prompt Positif")
        st.text_area("", result.get("positive", ""), height=200, key="positive_out")
    with col_n:
        st.markdown("### Prompt Negatif")
        st.text_area("", result.get("negative", ""), height=200, key="negative_out")

    st.markdown("---")
    col_save, col_gen = st.columns(2)
    with col_save:
        if st.button("💾 Simpan Prompt", use_container_width=True):
            ts = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
            outdir = os.path.join("..", "docs", "prompts")
            os.makedirs(outdir, exist_ok=True)
            path = os.path.join(outdir, f"prompt_{st.session_state.niche}_{ts}.json")
            with open(path, "w") as f:
                json.dump(result, f, indent=2)
            st.success(f"Tersimpan: {path}")
    with col_gen:
        if st.button("▶ Generate Video (Veo)", type="primary", use_container_width=True):
            st.session_state.step = 4
            st.rerun()

    col_back1, col_back2 = st.columns(2)
    with col_back1:
        if st.button("← Kembali ke Input", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with col_back2:
        if st.button("🏠 Beranda", use_container_width=True):
            st.session_state.step = 1
            st.rerun()

# --- LANGKAH 4: GENERATE VIDEO ---
elif st.session_state.step == 4:
    st.markdown("## Generate Video")
    result = st.session_state.result

    col1, col2 = st.columns(2)
    with col1:
        mode = st.selectbox("Tier Veo", ["lite", "fast", "standard"], index=0)
        audio = st.radio("Sertakan Audio", ["Tidak", "Ya"], index=0, horizontal=True)
    with col2:
        dur = st.number_input("Durasi (detik)", 4, 15, st.session_state.duration)

    st.markdown("**Prompt yang akan digunakan:**")
    st.info(result.get("positive", "")[:200] + "...")

    if st.button("🚀 Generate Sekarang", type="primary", use_container_width=True):
        from veo_provider.api_client import VeoClient
        with st.spinner("Membuat video (2-5 menit)..."):
            try:
                veo = VeoClient()
                veo.config["mode"] = mode
                veo.model_id = veo.config["model_ids"][mode]
                veo.default_config["generate_audio"] = (audio == "Ya")
                veo.default_config["duration_seconds"] = dur

                out = f"storage/results/video_{int(__import__('time').time())}.mp4"
                img_path = None
                if st.session_state.ref_image:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                    tmp.write(st.session_state.ref_image.getvalue())
                    img_path = tmp.name

                path = veo.generate_video(
                    prompt=result,
                    source_image_path=img_path,
                    output_filename=out,
                )
                if path:
                    st.success(f"✅ Video siap: {path}")
                    st.video(path)
                else:
                    st.error("❌ Gagal membuat video")
            except Exception as e:
                st.error(f"Error: {e}")

    col_back1, col_back2 = st.columns(2)
    with col_back1:
        if st.button("← Kembali ke Hasil Prompt", use_container_width=True):
            st.session_state.step = 3
            st.rerun()
    with col_back2:
        if st.button("🏠 Beranda", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
