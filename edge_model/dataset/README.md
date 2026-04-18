# Northern Blades — Dataset Pipeline

Complete, end-to-end pipeline for building the YOLOv11m-seg training dataset.

## Pipeline Order

```
Step 01 → Step 02 → Step 03 → Step 00 → Step 04 → Step 05 → Step 06
```

| Step | Script | What It Does | Where to Run |
|---|---|---|---|
| **01** | `01_download_uvh26.py` | Downloads top 2000 densest UVH-26 images | Colab or Local |
| **02** | `02_youtube_extractor.py` | Extracts frames from 3 Delhi CCTV videos | Colab or Local |
| **03** | `03_sam_mask_generator.py` | Converts bounding boxes → SAM polygon masks | **Colab (GPU)** |
| **00** | `00_weather_augment.py` | Adds fog/rain/smog/glare to 30% of images | Colab or Local |
| **04** | `04_finalize_dataset.py` | Splits train/val, generates YOLO YAML | Colab or Local |
| **05** | `05_train.py` | Trains YOLOv11m-seg (200 epochs, 640px) | **Colab (GPU)** |
| **06** | `06_validate.py` | Per-class metrics + FPS benchmark | **Colab (GPU)** |

## Quick Start on Colab

```python
# Cell 1: Install dependencies
!pip install ultralytics segment-anything albumentations yt-dlp huggingface_hub

# Download SAM checkpoint
!wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth

# Cell 2: Upload these scripts or clone your repo
# Then run in order:
!python 01_download_uvh26.py
!python 02_youtube_extractor.py
!python 03_sam_mask_generator.py
!python 00_weather_augment.py
!python 04_finalize_dataset.py
!python 05_train.py
!python 06_validate.py
```

## Output Structure

```
northern_blades_dataset/
├── images/
│   ├── all_raw/          ← All images (UVH + YouTube + augmented)
│   ├── train/            ← 90% split
│   └── val/              ← 10% split
├── labels/
│   ├── all_raw/          ← All YOLO polygon labels
│   ├── train/
│   └── val/
├── qc_samples/           ← 50 visual QC images (inspect these!)
├── uvh26_top_annotations.json
└── northern_blades.yaml  ← YOLO training config
```

## Class Mapping

| ID | Class | UVH-26 Sources |
|---|---|---|
| 0 | `Heavy_Motor` | Bus, Truck, Mini-bus, LCV, Van, Tempo |
| 1 | `Light_Motor` | Hatchback, Sedan, SUV, MUV |
| 2 | `Organic_Object` | Custom (YouTube labels only) |
| 3 | `Three_Wheeler` | Auto-rickshaw, E-rickshaw |
| 4 | `Two_Wheeler` | Motorcycle, Cycle |

