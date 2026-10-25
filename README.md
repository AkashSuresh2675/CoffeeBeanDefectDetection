# Coffee Bean Defect Detection: YOLO11 + EfficientNet-B0 Hybrid Pipeline

Automated coffee bean defect detection and classification system for B.Tech final semester project.

## Architecture

Two-stage computer vision hybrid pipeline:
1. **Stage 1 (Localization)**: **YOLO11n** detector trained on 640-resolution images with 9 defect classes to detect bounding boxes around individual coffee beans on imaging plates.
2. **Stage 2 (Fine Classification)**: **EfficientNet-B0** classifier fine-tuned on individual bean crops with ImageNet transfer learning to classify subtle defect morphology.

---

## Model Checkpoints

Saved in `hybrid_model/models/` (under GitHub file size limits):

| Model Component | Checkpoint File | Size | Notes |
| :--- | :--- | :--- | :--- |
| **Object Detector** | `hybrid_model/models/yolo11_stage2_best.pt` | ~5.5 MB | YOLO11n 640px stage-2 fine-tuned model |
| **Fine Classifier** | `hybrid_model/models/efficientnet_improved_best.pth` | ~48.7 MB | 9-class fine classifier head on EfficientNet-B0 |

---

## Class Taxonomy

### Detector (Stage 1) - 9 IDs (0 to 8)
Configured in `data_yolo11_9class.yaml`:
- `0`: BLACK
- `1`: BROKEN
- `2`: BROWN
- `3`: BigBroken
- `4`: IMMATURE
- `5`: INSECT
- `6`: MOLD
- `7`: PartlyBlack
- `8`: LIGHTFM_HEAVYFM (Aggregates foreign matter)

### Classifier (Stage 2) - 9 Categories
- `['BLACK', 'BROKEN', 'BROWN', 'BigBroken', 'IMMATURE', 'INSECT', 'MIXED', 'MOLD', 'PartlyBlack']`

Both predictions are exposed in the `/predict` API payload and the web UI results table.

---

## Setup & Installation

### 1. Prerequisites
Python 3.10+ recommended.

### 2. Create Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## Running the Web Application

Start the Flask backend from the project root:
```powershell
python webapp/backend/app.py
```
Open `http://127.0.0.1:5000` in your web browser. Upload an image of coffee beans to run inference, view marked defect bounding boxes, and inspect class distributions.

---

## Model Evaluation Scripts

### Evaluate YOLO11 Detector
```powershell
python evaluate_detector.py --split val --imgsz 640 --conf 0.25
```

### Evaluate EfficientNet-B0 Classifier
```powershell
python hybrid_model/evaluate_efficientnet.py --model-path hybrid_model/models/efficientnet_improved_best.pth
```

### Generate Paper Figures & Reports
```powershell
python generate_figures.py
python generate_review_figures.py
```

---

## Dataset Configuration Note

If running custom training or re-evaluation from dataset sources:
1. Extract dataset into `archive/datasets/`.
2. Ensure `path:` in `data_yolo11_9class.yaml` points to your dataset location (e.g. `./archive/datasets` or absolute path on your machine).
