import os
import sys
import argparse
from ultralytics import YOLO

def main():
    parser = argparse.ArgumentParser(description="Evaluate YOLO11 Detector on Coffee Bean Defect Dataset")
    parser.add_argument('--model-path', type=str,
                        default=os.path.join("runs", "detect", "runs", "detect", "yolo11_9class_corrected", "weights", "best.pt"),
                        help="Path to YOLO11 checkpoint (.pt)")
    parser.add_argument('--data-yaml', type=str,
                        default="data_yolo11_9class.yaml",
                        help="Path to dataset YAML file")
    parser.add_argument('--imgsz', type=int, default=320,
                        help="Validation image size (default: 320 to match training)")
    parser.add_argument('--conf', type=float, default=0.25,
                        help="Confidence threshold for validation (default: 0.25)")
    parser.add_argument('--iou', type=float, default=0.5,
                        help="NMS IoU threshold for validation (default: 0.5)")
    parser.add_argument('--split', type=str, default="val",
                        help="Split to evaluate: 'val' or 'test'")

    args = parser.parse_args()

    project_root = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.abspath(os.path.join(project_root, args.model_path)) if not os.path.isabs(args.model_path) else args.model_path
    data_yaml = os.path.abspath(os.path.join(project_root, args.data_yaml)) if not os.path.isabs(args.data_yaml) else args.data_yaml

    print("\n=======================================================")
    print("🎯 YOLO11 Detector Evaluation (Ultralytics Validation)")
    print("=======================================================")
    print(f"📦 Model Checkpoint : {model_path}")
    print(f"📄 Dataset YAML     : {data_yaml}")
    print(f"🖼️  Image Size       : {args.imgsz}")
    print(f"🎚️  Confidence Thresh: {args.conf}")
    print(f"🔲 IoU Threshold    : {args.iou}")
    print(f"📂 Split            : {args.split}")
    print("=======================================================\n")

    if not os.path.exists(model_path):
        print(f"[ERROR] Model checkpoint not found at: {model_path}")
        sys.exit(1)

    if not os.path.exists(data_yaml):
        print(f"[ERROR] Data YAML file not found at: {data_yaml}")
        sys.exit(1)

    # Load YOLO Model
    model = YOLO(model_path)

    print(f"[INFO] Evaluating detector on '{args.split}' split...")
    metrics = model.val(
        data=data_yaml,
        imgsz=args.imgsz,
        conf=args.conf,
        iou=args.iou,
        split=args.split,
        device="cpu",
        plots=False,
        verbose=True
    )

    print("\n-----------------------------------------------------------------------------------")
    print("📊 YOLO11 DETECTION METRICS SUMMARY")
    print("-----------------------------------------------------------------------------------")
    p = metrics.box.p.mean() if hasattr(metrics.box, 'p') and len(metrics.box.p) > 0 else metrics.box.mp
    r = metrics.box.r.mean() if hasattr(metrics.box, 'r') and len(metrics.box.r) > 0 else metrics.box.mr
    map50 = metrics.box.map50
    map50_95 = metrics.box.map

    print(f"Mean Precision (B)    : {p:.4f} ({p*100:.2f}%)")
    print(f"Mean Recall (B)       : {r:.4f} ({r*100:.2f}%)")
    print(f"mAP@50 (B)            : {map50:.4f} ({map50*100:.2f}%)")
    print(f"mAP@50-95 (B)         : {map50_95:.4f} ({map50_95*100:.2f}%)")
    print("-----------------------------------------------------------------------------------")

    # Per-class metrics
    class_names = model.names
    print("\n🏷️  PER-CLASS DETECTOR METRICS (Class Index -> Name):")
    print(f"{'Class ID':<10} {'Class Name':<20} {'Precision':<12} {'Recall':<12} {'mAP@50':<12} {'mAP@50-95':<12}")
    print("-" * 80)
    for cls_idx in range(len(class_names)):
        cls_name = class_names[cls_idx]
        cls_p = metrics.box.p[cls_idx] if hasattr(metrics.box, 'p') and len(metrics.box.p) > cls_idx else 0.0
        cls_r = metrics.box.r[cls_idx] if hasattr(metrics.box, 'r') and len(metrics.box.r) > cls_idx else 0.0
        cls_map50 = metrics.box.ap50[cls_idx] if hasattr(metrics.box, 'ap50') and len(metrics.box.ap50) > cls_idx else 0.0
        cls_map = metrics.box.ap[cls_idx] if hasattr(metrics.box, 'ap') and len(metrics.box.ap) > cls_idx else 0.0
        print(f"{cls_idx:<10} {cls_name:<20} {cls_p:<12.4f} {cls_r:<12.4f} {cls_map50:<12.4f} {cls_map:<12.4f}")
    print("-" * 80 + "\n")

if __name__ == '__main__':
    main()
