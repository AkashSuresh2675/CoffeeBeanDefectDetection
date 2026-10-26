import os
import sys
import cv2
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from ultralytics import YOLO

def get_efficientnet_b0_model(num_classes):
    try:
        from torchvision.models import efficientnet_b0
        model = efficientnet_b0(weights=None)
    except (ImportError, AttributeError):
        from torchvision.models import efficientnet_b0
        model = efficientnet_b0(pretrained=False)

    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model

def run_diagnostic():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    yolo_path = os.path.join(project_root, "hybrid_model", "models", "yolo11_stage2_best.pt")
    if not os.path.exists(yolo_path):
        yolo_path = os.path.join(project_root, "runs", "detect", "runs", "detect", "yolo11_stage2_640", "weights", "best.pt")
    if not os.path.exists(yolo_path):
        yolo_path = os.path.join(project_root, "runs", "detect", "runs", "detect", "yolo11_9class_corrected", "weights", "best.pt")
    if not os.path.exists(yolo_path):
        yolo_path = os.path.join(project_root, "runs", "detect", "train-5", "weights", "best.pt")
    
    effnet_path = os.path.join(project_root, "hybrid_model", "models", "efficientnet_improved_best.pth")
    if not os.path.exists(effnet_path):
        effnet_path = os.path.join(project_root, "hybrid_model", "models", "efficientnet_best.pth")

    print("\n===================================================================================")
    print("🔬 HYBRID MODEL DIAGNOSTIC (YOLO11 + EfficientNet-B0)")
    print("===================================================================================")
    print(f"📦 YOLO Model Path       : {yolo_path} (Exists: {os.path.exists(yolo_path)})")
    print(f"🧬 EfficientNet Checkpoint: {effnet_path} (Exists: {os.path.exists(effnet_path)})")
    
    # 1. Load Checkpoint & Verify Index Mapping
    checkpoint = torch.load(effnet_path, map_location=device)
    effnet_class_names = checkpoint.get('class_names', [])
    effnet_class_to_idx = checkpoint.get('class_to_idx', {})

    print("\n-----------------------------------------------------------------------------------")
    print("🔍 EFFICIENTNET CHECKPOINT CLASS MAPPING VERIFICATION")
    print("-----------------------------------------------------------------------------------")
    print(f"Epoch Trained    : {checkpoint.get('epoch')}")
    print(f"Best Val Accuracy: {checkpoint.get('best_val_acc'):.2f}%")
    print(f"Class Names ({len(effnet_class_names)}): {effnet_class_names}")
    print("Exact Class-to-Index Mapping:")
    for cls_name, idx in effnet_class_to_idx.items():
        print(f"   [{idx}] -> {cls_name}")

    # Load YOLO
    yolo_model = YOLO(yolo_path)

    # Load EfficientNet
    effnet_model = get_efficientnet_b0_model(num_classes=len(effnet_class_names))
    effnet_model.load_state_dict(checkpoint['model_state_dict'])
    effnet_model.to(device)
    effnet_model.eval()

    effnet_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])

    # Select Test Images across different defect categories
    test_categories = {
        'BLACK': os.path.join(project_root, "archive", "datasets", "DataCoffee_2022", "BLACK", "0.00-0.05", "img", "BLACK_20200802_090526_000-005_8.04g_157(1).jpg"),
        'BROKEN': os.path.join(project_root, "archive", "datasets", "DataCoffee_2022", "BROKEN", "0.02-0.05", "img", "BROKEN_20200810_485298_002-005_3,65g(1).jpg"),
        'INSECT': os.path.join(project_root, "archive", "datasets", "DataCoffee_2022", "INSECT", "0.02-0.10", "img", "INSECT_20200802_171238_002-010_6.53g_81(1).jpg"),
        'BigBroken': os.path.join(project_root, "archive", "datasets", "DataCoffee_2022", "BigBroken", "0.00-0.05", "img", "BigBroken_20201015_723338_000-005_3,80g_122(1).jpg")
    }

    # Execute Diagnostic on each test image
    for category_label, img_path in test_categories.items():
        print("\n===================================================================================")
        print(f"🖼️ TEST IMAGE CATEGORY: {category_label}")
        print(f"📁 Path: {img_path}")
        print("===================================================================================")

        if not os.path.exists(img_path):
            print(f"[ERROR] Test image path not found: {img_path}")
            continue

        img_bgr = cv2.imread(img_path)
        img_h, img_w, _ = img_bgr.shape

        # YOLO11 Inference
        yolo_results = yolo_model.predict(source=img_path, conf=0.25, save=False)
        boxes_data = yolo_results[0].boxes

        if boxes_data is None or len(boxes_data) == 0:
            print("[WARNING] No beans detected by YOLO11 at 25% threshold.")
            continue

        print(f"YOLO11 detected {len(boxes_data)} beans.\n")

        for idx, box in enumerate(boxes_data):
            xyxy = [float(v) for v in box.xyxy[0].tolist()]
            x1, y1, x2, y2 = xyxy
            yolo_conf = float(box.conf[0].item())
            yolo_cls_id = int(box.cls[0].item())
            yolo_cls_name = yolo_results[0].names.get(yolo_cls_id, f"Class_{yolo_cls_id}")

            # Crop
            crop_x1 = max(0, int(x1))
            crop_y1 = max(0, int(y1))
            crop_x2 = min(img_w, int(x2))
            crop_y2 = min(img_h, int(y2))

            crop_bgr = img_bgr[crop_y1:crop_y2, crop_x1:crop_x2]

            if crop_bgr.size == 0 or crop_bgr.shape[0] <= 2 or crop_bgr.shape[1] <= 2:
                print(f"Bean {idx+1}: [ERROR] Invalid crop dimensions {crop_bgr.shape}")
                continue

            crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
            pil_crop = Image.fromarray(crop_rgb)
            input_tensor = effnet_transform(pil_crop).unsqueeze(0).to(device)

            with torch.no_grad():
                outputs = effnet_model(input_tensor)
                probs = torch.softmax(outputs, dim=1)[0]
                top3_probs, top3_indices = torch.topk(probs, k=min(3, len(effnet_class_names)))

            top1_cls = effnet_class_names[top3_indices[0].item()]

            print(f"Bean {idx+1}:")
            print(f"YOLO confidence: {yolo_conf*100:.1f}% (YOLO class: {yolo_cls_name})")
            print(f"EfficientNet top-3 predictions:")
            for rank, (prob_val, cls_idx) in enumerate(zip(top3_probs, top3_indices), 1):
                c_name = effnet_class_names[cls_idx.item()]
                c_pct = prob_val.item() * 100.0
                print(f"  {rank}. {c_name} - {c_pct:.1f}%")
            print(f"Final class: {top1_cls}\n")

if __name__ == '__main__':
    run_diagnostic()
