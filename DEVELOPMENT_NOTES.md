# DEVELOPMENT NOTES — Gemini Proyek (Evolutionary Construction Orchestrator)

Dibuat: 2026-05-11
Proyek: AI-powered construction time-lapse video generation
Path: `C:\gemini-proyek\video_time_lapse\evolutionary_construction_orchestrator\`

---

## 1. Arsitektur Saat Ini

### Doc (`APP_ARCHITECTURE_VEO3.md`) vs Realita

| Komponen | Doc janjikan | Realita |
|---|---|---|
| `core/orchestrator.py` | Main controller logic | **Tidak ada** |
| `bridge/su_exporter.rb` | Ruby scripts for frame extraction | **Tidak ada** |
| `prompt_engine/components/` | 8-component logic | **Hanya `__init__.py` kosong** |
| `veo_provider/job_manager.py` | Async job tracking | **Tidak ada** |
| Storage/SQLite | Experiment tracking | **Tidak ada (cuma JSON file)** |
| Jinja2 templates | Template engine | **Tidak ada (cuma markdown)** |
| 8-component prompt | Subject, Action, Context, Style, Camera, Composition, Ambiance, Audio | **Hanya 3: character, scene, technical** |

### File yang Ada vs Kondisi

| File | LOC | Kondisi |
|---|---|---|
| `app/main.py` | 64 | CLI entry point — flag independen, tidak ada pipeline, hardcoded prompt/image |
| `app/core/logger.py` | 30 | Logger sederhana, hanya print + JSON log |
| `app/bridge/mcp_client.py` | 63 | JSON-RPC ke SketchUp, recv cuma 8192 bytes (risk truncation) |
| `app/prompt_engine/refiner.py` | 106 | Iterative refinement loop — bare `except:`, fallback asal |
| `app/prompt_engine/builder.py` | 24 | Load template + assemble, method `assemble()` join pake `\n\n` doang |
| `app/veo_provider/api_client.py` | 62 | Veo API call, polling 30s interval, langsung blocking |
| `app/renovator_flow.py` | 105 | 2-stage transition — prompt hardcoded, Gemini call decorative |
| `configs/veo_config.yaml` | 10 | Model `veo-2.0-generate-001`, durasi 5s, aspek 16:9 |
| `assets/media/main_production.py` | 103 | Standalone script, pake Veo 3.1 (beda model dari main app) |
| `assets/media/comparison_production.py` | 112 | Multi-clip sequential, 3 fase konstruksi |

### Non-Code Assets

- `assets/models/` — 3 SketchUp models (MTH_A2, B1+B2)
- `assets/media/` — 3 frame images (start, end, wireframe, depth map)
- `prompt_engine/templates/` — 5 markdown templates (meta, character, scene, technical, eval)
- `storage/registry/` — JSON job logs
- 3 GCP service account keys tercommit (production, dev, farah)

---

## 2. Masalah Utama

### P0 — Security
- 3 file JSON service account key (production, development, farah) tercommit
- `GOOGLE_APPLICATION_CREDENTIALS` diset dari env variable di runtime (seharusnya gcloud auth)
- Tidak ada `.gitignore`

### P1 — Pipeline Terputus
- `--sync`, `--build-prompt`, `--generate` adalah flag independen
- Output `--sync` (`model_info`) tidak otomatis di-pass ke `--build-prompt`
- Input `--build-prompt` hardcoded string, bukan hasil sync
- Input `--generate` hardcoded prompt + image path
- Tidak ada session/state antar fase

### P1 — Error Handling Lemah
- `except:` tanpa spesifikasi exception (refiner.py:58, 85)
- Fallback tidak meaningful (meta_plan isi `user_input`)
- `renovator_flow.py` Gemini call ditaruh di try tanpa fallback properly

### P2 — Code Quality
- Path hardcoded `C:/gemini-proyek/...` (windows-specific)
- Campur bahasa Indonesia-Inggris tidak konsisten
- `mcp_client.py` receive buffer terbatas 8192 bytes
- Renovator prompt hardcoded string, Gemini call cuma formalitas
- `genai.Client()` di-init ulang di 3 class berbeda (refiner, veo, renovator)

### P2 — Arsitektur
- Tidak ada orchestrator — business logic tersebar di main.py
- Tidak ada async — generate video blocking selama 2-5 menit
- Tidak ada retry mechanism
- Tidak ada job queue untuk batch processing

### P3 — Fitur Content Creation
- Tidak ada UI/web interface
- Tidak ada template library (hanya 1 domain: construction)
- Tidak ada post-processing (watermark, trim, branding)
- Tidak ada export ke YouTube/Google Drive
- Tidak ada versioning prompt history

---

## 3. Potensi / Unik Selling Point

| Feature | Strength | Status |
|---|---|---|
| Iterative refinement loop | AI-evaluate-AI, self-healing prompt | Implemented tapi bare minimum |
| MCP Bridge to SketchUp | Direct integration ke 3D modeling tool | Working prototype |
| Renovator Flow | 2-stage transition video | Implemented tapi prompt hardcoded |
| Template architecture | Modular prompt components | Working, tinggal expand |
| Multi-GCP project | Production + dev terpisah | Already set up |

---

## 4. Prioritas Rekomendasi

### P1 — Infrastruktur Dasar (minggu 1)

1. **Bikin `core/orchestrator.py`** — pipeline engine 4 fase yang nyambung
2. **Redesign CLI** — `--run-pipeline` mode, session state (JSON atau SQLite)
3. **Implementasi SQLite registry** — ganti JSON file
4. **Benerin error handling** — specific exceptions, retry logic, meaningful fallback
5. **Add `.gitignore`** — exclude *.json key files (simpan path doang)

### P2 — Content Creation Features (minggu 2-3)

6. **Template Library** — expand dari construction ke: real estate promo, product showcase, event recap
7. **Batch Generation** — generate N variation dari 1 prompt (beda seed, angle, durasi)
8. **Asset Manager** — katalog hasil + metadata (prompt, seed, veo model, tanggal)
9. **Video Post-processing** — watermark, trim intro/outro, merge scene

### P3 — Skalabilitas (minggu 3+)

10. **Async job queue** — Redis/Celery atau Python asyncio
11. **Output publish** — Google Drive API, YouTube API, atau S3
12. **Web UI minimal** — Streamlit atau FastAPI + React

---

## 5. Pertanyaan Diskusi (Belum Terjawab)

- Target konten: hanya konstruksi, real estate, atau general content creation?
- Audience: single user sendiri, atau tim?
- Platform output: YouTube, Instagram, Google Drive, lokal?
- Prioritas: kualitas video (better prompting) vs volume (automation pipeline)?
- Budget GCP: Veo pricing mahal — ada budget constraint?
- Model Veo: pake 2.0 (stabil) atau 3.1 (lebih bagus tapi lebih mahal)?

---

## 6. Catatan Teknis Lain

- `main_production.py` pake `veo-3.1-generate-001`, sementara config pake `veo-2.0-generate-001` — inkonsisten model
- 3 project ID berbeda: `x-victor-470014-t7` (prod), `gen-lang-client-0490181014` (dev), `gen-lang-client-0541956108` (asset/media)
- Perlu nentuin satu primary project biar tidak bingung billing
- `duration_seconds: 5` di YAML vs `8` di production scripts
