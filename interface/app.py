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
from prompt_library import PromptLibrary

st.set_page_config(page_title="Veo Content Factory", layout="wide", page_icon="🎬")

st.title("🎬 Veo Content Factory")

with st.sidebar:
    st.markdown("### 🧭 Navigasi")
    if st.button("🏠 Beranda", use_container_width=True):
        st.session_state.step = 1
        st.session_state.niche = None
        st.session_state.idea = ""
        st.session_state.result = None
        st.session_state.edited_prompt = ""
        st.rerun()
    step_now = st.session_state.get("step", 1)
    labels = {1: "Pilih Niche", 2: "Input Ide", 3: "Hasil Prompt", 4: "Generate Video"}
    for s, label in labels.items():
        mark = "▸" if s == step_now else " "
        st.markdown(f"{mark} **Langkah {s}:** {label}")

    st.markdown("---")
    with st.expander("📚 Library Prompt", expanded=False):
        lib = PromptLibrary()
        niche_filter = st.selectbox("Filter niche", ["Semua"] + [n["name"] for n in niches], key="lib_filter")
        if st.button("🔄 Muat Ulang", use_container_width=True):
            st.rerun()
        slug_filter = None
        if niche_filter != "Semua":
            slug_filter = next((n["slug"] for n in niches if n["name"] == niche_filter), None)
        saved = lib.list(niche=slug_filter, limit=20)
        if not saved:
            st.caption("Belum ada prompt tersimpan")
        for e in saved[:10]:
            label = f"⭐{e['score']} {e['user_input'][:30]}"
            if st.button(label, use_container_width=True, key=f"lib_{e['id']}"):
                st.session_state.result = {
                    "positive": e["positive"],
                    "negative": e["negative"],
                    "score": e["score"],
                    "iterations": e.get("iterations", []),
                }
                st.session_state.niche = e["niche"]
                st.session_state.edited_prompt = e["positive"]
                st.session_state.step = 3
                st.rerun()

st.markdown("---")

if "step" not in st.session_state:
    st.session_state.step = 1
    st.session_state.niche = None
    st.session_state.idea = ""
    st.session_state.result = None
    st.session_state.log = []
    st.session_state.edited_prompt = ""
    st.session_state.parent_id = None
    st.session_state.parent_context = None

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

    # Show continuation context if coming from "Lanjutkan Cerita"
    if st.session_state.parent_context:
        ctx = st.session_state.parent_context
        st.info(f"⏩ **Melanjutkan cerita dari:**\n_{ctx['previous_idea']}_")
        with st.expander("Lihat prompt sebelumnya"):
            st.code(ctx['previous_prompt'][:300] + ("..." if len(ctx['previous_prompt']) > 300 else ""), language="text")

    st.markdown("---")

    col1, col2 = st.columns([3, 2])

    with col1:
        placeholder = "Lanjutkan: " if st.session_state.parent_context else "Contoh: rumah mewah modern 2 lantai, kolam renang, taman minimalis..."
        idea = st.text_area(
            "Deskripsi Ide",
            placeholder=placeholder,
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
    lib = PromptLibrary()
    need_save = False

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
                st.session_state.edited_prompt = result.get("positive", "")
                log(f"✅ Prompt selesai — skor: {result.get('score', 'N/A')}/10")
                need_save = True
            except Exception as e:
                st.error(f"Gagal: {e}")
                st.session_state.result = {"positive": "Error", "negative": "", "score": 0}
                st.session_state.edited_prompt = ""

    result = st.session_state.result
    score = result.get("score", 0)

    st.markdown(f"## Hasil Prompt — {st.session_state.niche}")

    # Score + Iterations
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

    # Editable prompt
    prompt_pos = st.session_state.edited_prompt or result.get("positive", "")
    prompt_neg = result.get("negative", "")

    st.markdown(f"**Edit Prompt Positif** — `{len(prompt_pos)} karakter`")
    edited = st.text_area("", prompt_pos, height=200, key="editor_prompt")
    st.session_state.edited_prompt = edited

    if prompt_neg:
        st.markdown(f"**Prompt Negatif**")
        st.code(prompt_neg, language="text", line_numbers=True)

    st.markdown("---")

    # Action buttons
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("💾 Simpan Revisi", use_container_width=True):
            pid = lib.save({
                "niche": st.session_state.niche,
                "user_input": st.session_state.idea,
                "positive": st.session_state.edited_prompt,
                "negative": prompt_neg,
                "score": score,
                "feedback": fb,
                "iterations": iters,
                "parent_id": st.session_state.parent_id,
            })
            st.session_state.parent_id = pid
            st.success(f"✅ Tersimpan (ID: {pid[:8]}...)")
    with col2:
        if st.button("🔄 Generate Ulang", use_container_width=True):
            st.session_state.result = None
            st.session_state.edited_prompt = ""
            st.rerun()
    with col3:
        if st.button("⏩ Lanjutkan Cerita", use_container_width=True):
            pid = lib.save({
                "niche": st.session_state.niche,
                "user_input": st.session_state.idea,
                "positive": st.session_state.edited_prompt,
                "negative": prompt_neg,
                "score": score,
                "feedback": fb,
                "iterations": iters,
                "parent_id": st.session_state.parent_id,
            })
            st.session_state.parent_id = pid
            st.session_state.parent_context = {
                "niche": st.session_state.niche,
                "previous_prompt": st.session_state.edited_prompt,
                "previous_idea": st.session_state.idea,
            }
            st.session_state.step = 2
            st.rerun()
    with col4:
        if st.button("▶ Generate Video", type="primary", use_container_width=True):
            st.session_state.step = 4
            st.rerun()

    # Auto-save first result to library
    if need_save and score > 0 and edited:
        pid = lib.save({
            "niche": st.session_state.niche,
            "user_input": st.session_state.idea,
            "positive": edited,
            "negative": prompt_neg,
            "score": score,
            "feedback": fb,
            "iterations": iters,
            "parent_id": st.session_state.parent_id,
        })
        st.session_state.parent_id = pid

    st.markdown("---")
    col_back1, col_back2 = st.columns(2)
    with col_back1:
        if st.button("← Kembali ke Input", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with col_back2:
        if st.button("🏠 Beranda", use_container_width=True):
            st.session_state.step = 1
            st.session_state.parent_context = None
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
