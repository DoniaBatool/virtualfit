# VirtualFit — lets-scroll Landing Page
## Manual Asset Handoff Document

**Brand:** VirtualFit  
**Style:** Cinematic Photoreal — Professional  
**Camera:** Architecture A — Continuous Walkthrough (one smooth forward flight, no pull-backs)  
**Scenes:** 6  
**Total assets to generate:** 6 still images + 6 video clips  

---

## Brand Kit

| Role | Color | Hex |
|------|-------|-----|
| Background | Deep Navy | `#0A1628` |
| Primary Text | Pure White | `#FFFFFF` |
| Accent | Warm Gold | `#C9A84C` |
| Secondary | Steel Blue | `#2D4A6B` |
| Subtle | Slate | `#7A8FA6` |

**Tone:** Precise · Trustworthy · Innovative · Premium

---

## STYLE PREAMBLE (copy this EXACTLY into every image prompt)

```
Cinematic photoreal wide-angle photograph, ultra-high resolution 8K, 
tack-sharp focus, professional studio lighting with soft directional 
fills and subtle rim light, shallow depth of field with clean bokeh 
in background. Color palette dominated by deep navy (#0A1628), crisp 
white surfaces, warm gold metallic accents. Fashion industry aesthetic, 
architectural precision. Wide 3:2 landscape composition. Background: 
controlled interior architectural space — no sky, no outdoor horizon, 
no windows to outside. Centered focal subject, nothing essential at 
far edges. No text, no letters, no logos, no visible human faces.
```

---

## FREE TOOLS TO USE

### For Still Images (choose one):
| Tool | Free Tier | Best For |
|------|-----------|----------|
| **Ideogram.ai** | 10 free/day | Photoreal, follows prompts precisely |
| **Playground AI** | 100 free/day | High quality photoreal |
| **Flux.1 on HuggingFace** | Free (slower) | Best open-source photoreal |
| **Leonardo.ai** | 150 tokens/day | Excellent photoreal |

**Settings:** Always select **3:2 ratio**, highest resolution available

### For Video Clips (Architecture A — needs start-frame image):
| Tool | Free Tier | Start Frame Support |
|------|-----------|---------------------|
| **Kling AI** (kling.kuaishou.com) | 66 free credits/day | ✅ Yes — upload first frame |
| **Hailuo AI** (hailuoai.com) | Free daily credits | ✅ Yes |
| **Pika Labs** (pika.art) | Free tier | ✅ Yes — "animate from image" |

**Video Settings:** 16:9 ratio, 8 seconds per clip, highest quality, NO audio

---

## ARCHITECTURE A — How the chain works

```
Still_1 → [Leg 1 video] → extract last frame
                                    ↓ (this becomes start frame for Leg 2)
                          [Leg 2 video] → extract last frame
                                                    ↓
                                          [Leg 3 video] → ...and so on

NO connectors needed — legs chain directly into each other.
Each leg's START FRAME = previous leg's LAST FRAME (extracted with ffmpeg or screenshot).
```

**IMPORTANT:** Leg 1 starts from Still_1. After Leg 1 is generated, extract its last frame (screenshot the final frame or use ffmpeg: `ffmpeg -sseof -0.1 -i leg1.mp4 -frames:v 1 leg1_last.png`). This becomes the start frame for Leg 2.

---

## ASSET STATUS TRACKER

| Asset | Prompt File | Status | Filename to Save As |
|-------|-------------|--------|---------------------|
| Still 1 | `prompts/still_1_fabric.txt` | ⬜ pending | `assets/still_1_fabric.jpg` |
| Still 2 | `prompts/still_2_studio.txt` | ⬜ pending | `assets/still_2_studio.jpg` |
| Still 3 | `prompts/still_3_factory.txt` | ⬜ pending | `assets/still_3_factory.jpg` |
| Still 4 | `prompts/still_4_store.txt` | ⬜ pending | `assets/still_4_store.jpg` |
| Still 5 | `prompts/still_5_fitting.txt` | ⬜ pending | `assets/still_5_fitting.jpg` |
| Still 6 | `prompts/still_6_hero.txt` | ⬜ pending | `assets/still_6_hero.jpg` |
| Leg 1 Video | `prompts/leg_1_fabric.txt` | ⬜ pending (needs Still 1 as start) | `assets/vid/leg_1.mp4` |
| Leg 2 Video | `prompts/leg_2_studio.txt` | ⬜ pending (needs Leg 1 last frame) | `assets/vid/leg_2.mp4` |
| Leg 3 Video | `prompts/leg_3_factory.txt` | ⬜ pending (needs Leg 2 last frame) | `assets/vid/leg_3.mp4` |
| Leg 4 Video | `prompts/leg_4_store.txt` | ⬜ pending (needs Leg 3 last frame) | `assets/vid/leg_4.mp4` |
| Leg 5 Video | `prompts/leg_5_fitting.txt` | ⬜ pending (needs Leg 4 last frame) | `assets/vid/leg_5.mp4` |
| Leg 6 Video | `prompts/leg_6_hero.txt` | ⬜ pending (needs Leg 5 last frame) | `assets/vid/leg_6.mp4` |

**Update status:** ⬜ pending → 🔄 generating → ✅ done → ❌ redo

---

## GENERATION ORDER

1. Generate ALL 6 still images first (can be done in parallel)
2. Generate Leg 1 video using Still 1 as start frame
3. Extract Leg 1's last frame → use as start for Leg 2
4. Generate Leg 2 → extract last frame → Leg 3
5. Continue sequentially through Leg 6

---

## SCENE JOURNEY

| # | Scene | Eyebrow | Headline | Body |
|---|-------|---------|----------|------|
| 1 | Premium Fabric Warehouse | FROM FIBER TO FASHION | Every thread, chosen. | We begin where fashion begins — with the finest materials, selected by AI to match your exact measurements. |
| 2 | AI Design Studio | DESIGNED FOR YOU | Your body. Your style. | Our models analyze 10,000+ garment patterns to find cuts that are engineered for your proportions. |
| 3 | Smart Manufacturing | BUILT WITH PRECISION | Zero compromise. | Automated production lines ensure every seam, every stitch meets exact specifications. |
| 4 | Curated Store | CURATED COLLECTION | Only what fits you. | Your personal catalog — 50,000+ garments filtered by AI to show only what works for your body type. |
| 5 | Virtual Fitting Room | TRY IT ON NOW | See yourself in it. | Upload your photo. Select any garment. See the result in under 15 seconds — no dressing room needed. |
| 6 | Perfect Fit (Hero) | YOUR PERFECT FIT | Confidence delivered. | Try VirtualFit free — the future of fashion is knowing exactly how it looks before you buy. |
