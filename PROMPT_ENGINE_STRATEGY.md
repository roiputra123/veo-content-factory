# PROMPT ENGINE STRATEGY — Veo 3 Content Factory

Dibuat: 2026-05-11
Berdasarkan riset Google Veo 3 prompting guide, best practices, dan kode existing.

---

## 1. Masalah Prompt Pipeline Saat Ini

### Text-to-Video (dari prompt saja)

| Masalah | Kondisi Sekarang | Seharusnya |
|---|---|---|
| Komponen prompt | 3 (character, scene, technical) | 5-part formula: Cinematography + Subject + Action + Context + Style/Audio |
| Cinematography | Tidak ada | Wajib: camera angle, movement, lens, composition |
| Audio | Tidak ada | Setiap prompt perlu: ambience, SFX, atau music direction |
| Negative prompt | Tidak ada | Veo 3 support — wajib untuk production |
| Domain template | Generic (scientist, librarian) | Per niche: construction, product, travel, cooking, tech |
| `(thats where the camera is)` | Disebut di template teknis | Wajib konsisten di setiap prompt |
| Lighting | Tidak disebut | Veo 3 strongest di lighting — harus eksplisit |

### Image-to-Video (dari gambar referensi)

| Masalah | Kondisi Sekarang | Seharusnya |
|---|---|---|
| Prompt | Deskripsi penuh dari awal | **Hanya motion** — gambar sudah kasih subject+scene+style |
| Image analysis | Tidak ada | Wajib analisis gambar dulu biar tau mana yang jangan diulang |
| Motion description | Tidak spesifik | Harus: arah gerak, kecepatan, perubahan apa yang terjadi |

---

## 2. Arsitektur Prompt Engine yang Disarankan

```
INPUT: text prompt ATAU text + image
                │
      ┌─────────▼─────────┐
      │  CONTENT CLASSIFIER│  ← LLM tentuin: ini construction?
      │  (1x panggil LLM)  │     cooking? tech review? travel?
      └─────────┬─────────┘
                │
      ┌─────────▼─────────┐
      │  NICHE PROFILE     │  ← YAML per niche: tone, vocab, style
      │  (YAML loader)     │     camera default, audio style
      └─────────┬─────────┘
                │
      ┌─────────▼─────────┐
      │  IMAGE ANALYZER    │  ← HANYA jika ada gambar referensi
      │  (1x panggil LLM)  │     Output: apa yang SUDAH ada di gambar
      │                    │     (jangan diulang di prompt)
      └─────────┬─────────┘
                │
      ┌─────────▼──────────────────┐
      │  5-PART PROMPT GENERATOR   │  ← Cinematography + Subject
      │  (5x panggil LLM, 1 per    │     + Action + Context + Style
      │   komponen, bisa paralel)   │     + Audio + Negative
      └─────────┬──────────────────┘
                │
      ┌─────────▼─────────┐
      │  EVALUATOR        │  ← LLM nilai prompt 1-10
      │  (1x panggil LLM) │     feedback → loop max 3x
      └─────────┬─────────┘
                │
      ┌─────────▼─────────┐
      │  OUTPUT ASSEMBLER  │  → positive_prompt: string
      │                    │  → negative_prompt: string (jika ada)
      │                    │  → seed: random atau tetap
      └───────────────────┘
```

---

## 3. 5-Part Formula (Wajib untuk Veo 3)

### Formula

```
[Cinematography] + [Subject] + [Action] + [Context] + [Style & Ambiance] + [Audio]
```

### Contoh Prompt Construction yang Benar (Text-to-Video)

> Low-angle crane shot starting close to foundation and slowly rising (thats where the camera is). A modern luxury villa with clean geometric lines, large glass windows, and natural stone facade. Construction workers in hard hats and orange vests are pouring concrete foundation, scaffolding rising around the structure. Empty lot in an upscale suburban development, golden hour sunset lighting, dust particles floating in warm air. Cinematic, hyper-realistic, architectural visualization style with shallow depth of field. Audio: sounds of construction site, concrete mixer rumbling, workers calling out, distant birds.

### Contoh Prompt Construction untuk Image-to-Video (Hanya Motion)

> Gentle camera pan from left to right (thats where the camera is). Workers begin moving, concrete slowly pours from the mixer truck, scaffolding rises upward, shadows lengthen as the sun moves across the sky. Hyper-lapse speed. Audio: time-lapse whoosh sound, construction ambience.

---

## 4. Image Analyzer Module (WAJIB untuk Image-to-Video)

Tugas: analisis gambar referensi dan output JSON tentang apa yang SUDAH ada.

### Output JSON

```json
{
  "existing_elements": {
    "subject": "luxury villa, modern, glass facade",
    "camera_position": "frontal, eye-level",
    "lighting": "golden hour, warm",
    "materials": ["glass", "stone", "concrete"],
    "construction_stage": "foundation",
    "background": "suburban development, empty lots"
  },
  "do_not_redescribe": [
    "facade materials",
    "building design",
    "camera position",
    "time of day"
  ],
  "suggested_motion": [
    "workers pouring concrete",
    "scaffolding rising",
    "crane arm swinging"
  ]
}
```

### Logika

```
Prompt final = MOTION ONLY (dari suggested_motion)
             + camera change (jika ada perubahan POV)
             + audio
```

JANGAN redeskripsi `do_not_redescribe`.

---

## 5. Negative Prompt Generator

### Default per Niche

```yaml
# construction.yaml
negative: >
  blurry, distorted, deformed, low quality, watermark, text overlay,
  subtitle, cartoon, unrealistic materials, floating objects,
  unnatural lighting, glitch artifacts, inconsistent shadows,
  missing reflections, flat lighting, oversaturated

# product.yaml
negative: >
  blurry, distorted, deformed, low quality, watermark, text overlay,
  dirty lens, chromatic aberration, motion blur, inconsistent reflections,
  floating objects, unrealistic shadows

# cooking.yaml
negative: >
  blurry, distorted, deformed, low quality, watermark, text overlay,
  raw food, burnt, unnatural colors, plastic-looking ingredients,
  floating objects, inconsistent shadows
```

### Cara Kerja

- Ambil default dari niche profile
- Jika image analyzer menemukan elemen tertentu, tambahkan negative spesifik
- Contoh: gambar di dalam ruangan → tambahkan `"overexposed outdoor light"`

---

## 6. Niche Profile System (YAML per Content Type)

### Contoh `construction.yaml`

```yaml
name: construction
prompt_formula: "5-part"

cinematography:
  camera_default: "crane shot, slow dolly-in"
  angles: ["low-angle", "aerial", "frontal", "45-degree"]
  movements: ["dolly-in", "crane up", "pan", "tracking"]
  lens: "wide-angle, 24mm"

subject:
  default: "modern luxury villa, clean geometric lines"
  vocabulary: ["facade", "foundation", "scaffolding", "columns", "glass panels", "stone cladding"]

action:
  vocabulary: ["pouring concrete", "rising scaffolding", "installing windows", "landscaping", "painting"]
  speed: ["hyper-lapse", "time-lapse", "slow motion"]

context:
  environment: ["suburban development", "construction site", "empty lot"]
  lighting_default: "golden hour, warm sunlight, soft shadows"

style:
  visual: "photorealistic, architectural visualization, hyper-detailed"
  mood: "professional, cinematic, aspirational"

audio:
  ambience: "construction site sounds, distant machinery"
  music: "cinematic orchestral, building tension"
  negative_audio: "no speech, no dialogue"

negative: "blurry, distorted, deformed, low quality, watermark, text overlay, subtitle, cartoon, unrealistic materials, floating objects, unnatural lighting, glitch artifacts, inconsistent shadows, missing reflections, flat lighting, oversaturated"

duration: 8
aspect_ratio: "16:9"
```

### Contoh `cooking.yaml`

```yaml
name: cooking
prompt_formula: "5-part"

cinematography:
  camera_default: "overhead top-down shot"
  angles: ["top-down", "45-degree", "eye-level", "close-up"]
  movements: ["dolly-in", "slow push-in", "static"]
  lens: "macro lens, shallow depth of field"

subject:
  default: "fresh ingredients on wooden cutting board"
  vocabulary: ["steaming", "sizzling", "chopping", "mixing", "pouring"]

action:
  vocabulary: ["chopping vegetables", "stirring sauce", "kneading dough", "pouring oil", "sprinkling seasoning"]
  speed: ["real-time", "slight slow-motion"]

context:
  environment: ["modern kitchen", "rustic kitchen", "marble countertop"]
  lighting_default: "soft window light, warm, natural"

style:
  visual: "photorealistic, food photography style, vibrant colors"
  mood: "warm, inviting, cozy"

audio:
  ambience: "sizzling sounds, chopping, kitchen ambience"
  music: "upbeat acoustic, light jazz"
  negative_audio: "no speech, no dialogue, no heavy music"

negative: "blurry, distorted, deformed, low quality, watermark, text overlay, raw food, burnt, unnatural colors, plastic-looking ingredients, floating objects, inconsistent shadows"

duration: 5
aspect_ratio: "9:16"
```

---

## 7. Evaluator Prompt (Template)

```
You are a meticulous prompt engineering evaluator for Veo 3 text-to-video AI model.

Evaluate this prompt on 5 criteria (score 1-10 each):
1. COMPLETENESS: Does it have all 5 parts? (Cinematography, Subject, Action, Context, Style/Audio)
2. CLARITY: Is the language specific and unambiguous?
3. IMAGE-TO-VIDEO AWARENESS: If reference image is used, does it ONLY describe motion?
4. TECHNICAL QUALITY: Are camera angle, movement, lens specified? Is "(thats where the camera is)" used?
5. NEGATIVE PROMPT: Are unwanted elements excluded?

Output JSON:
{
  "score": <average 1-10>,
  "breakdown": {
    "completeness": <1-10>,
    "clarity": <1-10>,
    "image_to_video": <1-10>,
    "technical_quality": <1-10>,
    "negative_prompt": <1-10>
  },
  "feedback": ["list of specific improvements"],
  "suggested_fixes": "rewritten improved prompt"
}
```

---

## 8. Template Per Niche (Minimal 5 untuk Mulai)

| Niche | Camera Default | Lighting Default | Audio Default | Durasi |
|---|---|---|---|---|
| **Construction** | Crane shot, dolly-in | Golden hour, warm | Construction ambience + cinematic orchestral | 8s |
| **Product Showcase** | Turntable, macro lens | Soft studio, diffused | Ambient electronic, subtle whoosh | 5s |
| **Travel/Nature** | Wide angle, tracking | Natural golden hour | Nature ambience, birds, wind | 8s |
| **Cooking/Food** | Top-down, overhead | Soft window light | Sizzling, chopping, upbeat acoustic | 5s |
| **Tech Review** | Medium shot, desk | Cool key light, rim | Soft hum, keyboard clicks | 5s |

---

## 9. Biaya Operasional

### LLM (Prompt Engineering) — Hampir Gratis

| Model | Input/1M tokens | Output/1M tokens | Biaya per prompt (~10K token) |
|---|---|---|---|
| Gemini 1.5 Flash | $0.075 | $0.30 | ~$0.00075 |
| Gemini 1.5 Pro (saat ini) | $1.25 | $5.00 | ~$0.0125 |
| Gemini 2.0 Flash-Lite | $0.075 | $0.30 | ~$0.00075 |

**Rekomendasi:** Pake Flash untuk semua prompt engineering. Pro hanya untuk final evaluation.

### Video Generation (Veo 3)

| Tier | Tanpa Audio | Dengan Audio | Free Tier |
|---|---|---|---|
| Veo 3.1 Lite | $0.03/dtk | $0.05/dtk | — |
| Veo 3.1 Fast | $0.08/dtk | $0.10/dtk | — |
| Veo 3.1 Standard | $0.20/dtk | $0.40/dtk | — |
| Gemini Advanced | — | — | $19.99/bln (termasuk Google One) |
| Google AI Ultra | — | — | $249.99/bln (high volume) |

### Estimasi Video

| Skenario | Biaya |
|---|---|
| 1 video 8s (Lite, no audio) | $0.24 |
| 1 video 8s (Fast, with audio) | $0.80 |
| 1 video 8s (Standard, with audio) | $3.20 |
| 100 video/bulan (Lite, no audio) | $24 |
| 100 video/bulan (Fast, with audio) | $80 |

---

## 10. Prioritas Implementasi

### Urutan Pengerjaan

1. **Bikin 5 template per niche** — construction, product, travel, cooking, tech
   - File: `app/prompt_engine/niches/construction.yaml`, dll.
   - Loader: `app/prompt_engine/niche_loader.py`

2. **Bikin `image_analyzer.py`** — ini game-changer untuk image-to-video
   - File: `app/prompt_engine/image_analyzer.py`
   - Input: path gambar
   - Output: JSON (existing_elements, do_not_redescribe, suggested_motion)

3. **Restruktur `refiner.py`** — dari 3 component jadi 5-part formula
   - Template baru: `cinematography.md`, `subject.md`, `action.md`, `context.md`, `style_audio.md`
   - Hapus template lama: `c_character_development.md`, `d_scene_architecture.md`, `e_technical_specification.md`

4. **Bikin negative prompt generator**
   - File: `app/prompt_engine/negative_builder.py`
   - Gabung default niche + hasil image analyzer

5. **Update `veo_config.yaml`** — tambah mode tier (lite/fast/standard)
   - Default: `lite` untuk dev
   - Auto-switch ke model sesuai mode

6. **Test loop: generate → evaluate → iterate**
   - Evaluator template udah ada (`h_prompt_evaluation.md`)
   - Tinggal refine skor minimum dan feedback loop

---

## 11. Catatan Kunci

### Image-to-Video Golden Rule

> **JANGAN redeskripsi apa yang sudah ada di gambar referensi.**
> Prompt hanya untuk: gerakan, perubahan, audio.

### Prompt Length

- Veo 3 weight early tokens lebih berat
- Front-load informasi penting: camera + subject + action dalam 3 kalimat pertama
- Ideal: 3-6 kalimat per prompt

### Audio Strategy

- Generate tanpa audio Veo = lebih murah $0.10/dtk
- Tambah audio sendiri pake tools gratis (CapCut, FFmpeg, atau AI TTS)
- Kecuali butuh lip-sync dialog — baru pake Veo with audio

### Seed Parameter

- Simpan seed setiap generate → kalau hasil bagus bisa reproduce
- Seed berbeda = variasi dari prompt yang sama
- Implementasi: tambah parameter `seed` di config

### Batch vs Sequential

- Untuk multi-scene video (misal: renovasi 3 tahap), generate sequential
- Frame terakhir klip 1 = start frame klip 2
- Prompt klip 2 harus deskripsikan transisi dari klip 1

---

## 12. Referensi

- Google Veo 3.1 Prompt Guide: `https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1`
- Veo Prompt Best Practices: `https://cloud.google.com/vertex-ai/generative-ai/docs/video/best-practice`
- snubroot/Veo-3-Meta-Framework (GitHub) — 5-part formula reference
- ShaheerKhawaja/awesome-ai-video-prompts (GitHub) — curated prompt collection
- Eric-Lautanen/seamless-ai-video-prompt-template (GitHub) — last-frame workflow
