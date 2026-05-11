# Veo Content Factory

AI-powered video content generation pipeline for real estate marketing.
Uses Google Veo 3 for video generation + Gemini for prompt engineering.

## Struktur

```
veo-content-factory/
├── app/
│   ├── main.py                        CLI entry point
│   ├── prompt_engine/
│   │   ├── refiner.py                 Iterative prompt refinement loop
│   │   ├── builder.py                 Prompt assembly from components
│   │   ├── niche_loader.py            Load YAML niche profiles
│   │   ├── image_analyzer.py          Analyze reference images (TODO)
│   │   ├── negative_builder.py        Generate negative prompts (TODO)
│   │   ├── niches/                    10 real estate niche YAMLs
│   │   └── templates/                 5-part formula templates
│   ├── veo_provider/
│   │   └── api_client.py             Veo 3 video generation client
│   ├── bridge/
│   │   └── mcp_client.py             SketchUp MCP bridge
│   └── core/
│       └── logger.py                  Production job logger
├── interface/
│   └── app.py                        Streamlit UI
├── assets/
│   └── media/                        Reference images
├── docs/                             Prompt exports
├── .env.example                      Environment template
└── requirements.txt
```

## 10 Niche Real Estate

1. **Property Cinematic Tour** — Walkthrough properti
2. **Construction Time-lapse** — Pembangunan dari awal
3. **Renovation Reveal** — Sebelum vs sesudah
4. **Interior Design Detail** — Fokus desain interior
5. **Architecture Exterior** — Fasad dan landscape
6. **Neighborhood Lifestyle** — Lingkungan perumahan
7. **Aerial Masterplan** — Kawasan dari atas
8. **Marketing Teaser 5s** — Iklan pendek sosial media
9. **Virtual Staging** — Ruang kosong → berisi furnitur
10. **Comparison Progress** — Tahap konstruksi

## Cara Pakai

```bash
pip install -r requirements.txt
cp .env.example .env
# isi .env dengan path key + project ID
streamlit run interface/app.py
```
