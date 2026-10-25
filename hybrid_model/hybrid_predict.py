import os
import sys
import argparse
import cv2
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from ultralytics import YOLO

# Default Class List matching data.yaml and dataset folders
DEFAULT_CLASSES = [
    'BLACK', 'BROKEN', 'BROWN', 'BigBroken',
    'IMMATURE', 'INSECT', 'MIXED', 'MOLD', 'PartlyBlack'
]

# Color palette for defect category bounding box visualization (BGR format)
CLASS_COLOR_MAP = {
    'BigBroken': (34, 139, 34),       # Forest Green
    'BLACK': (40, 40, 40),            # Dark Gray/Black
    'BROKEN': (0, 69, 255),           # Orange Red
    'BROWN': (19, 69, 139),           # Saddle Brown
    'IMMATURE': (50, 205, 50),        # Lime Green
    'INSECT': (128, 0, 128),          # Purple
    'MIXED': (0, 165, 255),           # Orange
    'MOLD': (205, 90, 106),           # Steel Blue
    'PartlyBlack': (80, 80, 80),      # Medium Gray
    'LIGHTFM_HEAVYFM': (0, 140, 255)  # Amber / Dark Orange (Detector class 8)
}

def get_efficientnet_b0_model(num_classes=9):
    """
    Constructs an EfficientNet-B0 architecture and replaces the classifier head.
    """
    try:
        from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
        model = efficientnet_b0(weights=None)
    except (ImportError, AttributeError):
        from torchvision.models import efficientnet_b0
        model = efficientnet_b0(pretrained=False)

    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model

class HybridCoffeePredictor:
    """
    Independent Hybrid Coffee Bean Defect Predictor
    Architecture: YOLO11 Object Detector -> Bounding Box Crop -> EfficientNet-B0 Classifier
    """
    def __init__(self, yolo_path=None, effnet_path=None):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(self.script_dir)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # 1. Resolve YOLO11 Weight Path
        if yolo_path is None:
            # Check models directory first
            cand_model_dir = os.path.join(self.project_root, "hybrid_model", "models", "yolo11_stage2_best.pt")
            cand_stage2 = os.path.join(self.project_root, "runs", "detect", "runs", "detect", "yolo11_stage2_640", "weights", "best.pt")
            cand_corrected = os.path.join(self.project_root, "runs", "detect", "runs", "detect", "yolo11_9class_corrected", "weights", "best.pt")
            if os.path.exists(cand_model_dir):
                yolo_path = cand_model_dir
            elif os.path.exists(cand_stage2):
                yolo_path = cand_stage2
            elif os.path.exists(cand_corrected):
                yolo_path = cand_corrected
            else:
                yolo_path = os.path.join(self.project_root, "runs", "detect", "train-5", "weights", "best.pt")
                if not os.path.exists(yolo_path):
                    # Search runs/detect for alternative best.pt
                    runs_dir = os.path.join(self.project_root, "runs", "detect")
                    if os.path.exists(runs_dir):
                        for run_name in sorted(os.listdir(runs_dir), reverse=True):
                            candidate = os.path.join(runs_dir, run_name, "weights", "best.pt")
                            if os.path.exists(candidate):
                                yolo_path = candidate
                                break

        self.yolo_path = os.path.abspath(yolo_path)

        # 2. Resolve EfficientNet Checkpoint Path
        if effnet_path is None:
            cand_eff = os.path.join(self.project_root, "hybrid_model", "models", "efficientnet_improved_best.pth")
            if os.path.exists(cand_eff):
                effnet_path = cand_eff
            else:
                effnet_path = os.path.join(self.project_root, "hybrid_model", "models", "efficientnet_best.pth")
        
        self.effnet_path = os.path.abspath(effnet_path)

        # Validate file existence
        if not os.path.exists(self.yolo_path):
            raise FileNotFoundError(f"[ERROR] YOLO11 weight file not found at: {self.yolo_path}")
        
        if not os.path.exists(self.effnet_path):
            raise FileNotFoundError(f"[ERROR] EfficientNet checkpoint file not found at: {self.effnet_path}")

        # Load YOLO Model
        print(f"[INFO] Loading YOLO11 Detector: {self.yolo_path}")
        self.yolo_model = YOLO(self.yolo_path)

        # Load EfficientNet Model
        print(f"[INFO] Loading EfficientNet-B0 Classifier: {self.effnet_path}")
        checkpoint = torch.load(self.effnet_path, map_location=self.device)
        
        self.class_names = checkpoint.get('class_names', DEFAULT_CLASSES)
        self.effnet_model = get_efficientnet_b0_model(num_classes=len(self.class_names))
        self.effnet_model.load_state_dict(checkpoint['model_state_dict'])
        self.effnet_model.to(self.device)
        self.effnet_model.eval()

        # ImageNet Preprocessing Transforms
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    def predict(self, image_path, conf_threshold=0.25, iou_threshold=0.45, imgsz=640):
        """
        Executes the hybrid prediction pipeline on an input image.
        
        Args:
            image_path (str): Path to input image file.
            conf_threshold (float): Confidence threshold for YOLO detection.
            iou_threshold (float): IoU/NMS threshold for YOLO detection.
            imgsz (int): Image size resolution for YOLO inference (default: 640).
            
        Returns:
            results (list of dicts): Detection & classification details for every detected bean.
            annotated_image (numpy ndarray): OpenCV image with bounding boxes & labels.
        """
        image_path = os.path.abspath(image_path)
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"[ERROR] Input image not found: {image_path}")

        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise ValueError(f"[ERROR] Could not decode image file: {image_path}")

        img_h, img_w, _ = img_bgr.shape
        annotated_bgr = img_bgr.copy()

        # Step 1: YOLO11 Object Detection (Bean Detection & Localization at 640 resolution)
        yolo_results = self.yolo_model.predict(
            source=image_path,
            conf=conf_threshold,
            iou=iou_threshold,
            imgsz=imgsz,
            save=False
        )
        boxes_data = yolo_results[0].boxes

        hybrid_results = []

        if boxes_data is not None and len(boxes_data) > 0:
            for idx, box in enumerate(boxes_data):
                # Coordinates
                xyxy = [float(v) for v in box.xyxy[0].tolist()]
                x1, y1, x2, y2 = xyxy
                yolo_conf = float(box.conf[0].item())
                yolo_cls_id = int(box.cls[0].item())
                yolo_cls_name = yolo_results[0].names.get(yolo_cls_id, f"Class_{yolo_cls_id}")

                # Step 2: Bounding Box Image Patch Cropping
                crop_x1 = max(0, int(x1))
                crop_y1 = max(0, int(y1))
                crop_x2 = min(img_w, int(x2))
                crop_y2 = min(img_h, int(y2))

                crop_bgr = img_bgr[crop_y1:crop_y2, crop_x1:crop_x2]

                eff_class_name = yolo_cls_name
                eff_conf = yolo_conf
                eff_class_id = yolo_cls_id

                # Step 3: EfficientNet-B0 Classification on Cropped Patch
                if crop_bgr.size > 0 and crop_bgr.shape[0] > 2 and crop_bgr.shape[1] > 2:
                    try:
                        crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
                        pil_crop = Image.fromarray(crop_rgb)
                        input_tensor = self.transform(pil_crop).unsqueeze(0).to(self.device)

                        with torch.no_grad():
                            outputs = self.effnet_model(input_tensor)
                            probs = torch.softmax(outputs, dim=1)
                            top_prob, top_idx = torch.max(probs, dim=1)

                            eff_conf = float(top_prob.item())
                            eff_class_id = int(top_idx.item())
                            if eff_class_id < len(self.class_names):
                                eff_class_name = self.class_names[eff_class_id]
                    except Exception as err:
                        print(f"[WARNING] Crop classification error on bean #{idx+1}: {err}")

                # Build detection record preserving both YOLO and EfficientNet outputs
                record = {
                    'bean_id': idx + 1,
                    'yolo_confidence': round(yolo_conf * 100, 1),
                    'yolo_class': yolo_cls_name,
                    'effnet_classification': eff_class_name,
                    'effnet_confidence': round(eff_conf * 100, 1),
                    'final_result': eff_class_name,
                    'confidence_score': round(eff_conf, 4),
                    'bbox': [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)]
                }
                hybrid_results.append(record)

                # Step 4: Draw Clean, Non-Intrusive Bounding Box & Label Tag
                # Scale-aware dynamic sizing for high-res images (e.g. 2560x1920)
                img_max_dim = max(img_w, img_h)
                scale = max(0.8, img_max_dim / 1600.0)
                box_thickness = max(2, int(round(scale * 1.5)))
                font_scale = max(0.40, round(scale * 0.38, 2))
                font_thickness = max(1, int(round(scale * 0.9)))

                box_color = CLASS_COLOR_MAP.get(eff_class_name, (0, 220, 100))
                
                # Draw rounded rectangle outline for bean
                cv2.rectangle(annotated_bgr, (crop_x1, crop_y1), (crop_x2, crop_y2), box_color, box_thickness)

                # Compact tag text
                label_text = f"#{idx+1} {eff_class_name} {int(eff_conf * 100)}%"
                (font_w, font_h), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)

                pad_x = int(4 * scale)
                pad_y = int(3 * scale)

                # Position label tag cleanly above or inside box top edge
                tag_y2 = crop_y1 - 2
                tag_y1 = tag_y2 - font_h - (pad_y * 2)
                if tag_y1 < 0:
                    tag_y1 = crop_y1 + 2
                    tag_y2 = tag_y1 + font_h + (pad_y * 2)

                tag_x1 = crop_x1
                tag_x2 = min(img_w, crop_x1 + font_w + (pad_x * 2))

                # Background badge with dark border
                cv2.rectangle(annotated_bgr, (tag_x1, tag_y1), (tag_x2, tag_y2), box_color, -1)
                cv2.rectangle(annotated_bgr, (tag_x1, tag_y1), (tag_x2, tag_y2), (20, 20, 20), 1)

                text_x = tag_x1 + pad_x
                text_y = tag_y2 - pad_y - baseline // 2
                cv2.putText(annotated_bgr, label_text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)

        return hybrid_results, annotated_bgr

def main():
    parser = argparse.ArgumentParser(description="Standalone Hybrid Coffee Bean Defect Inference (YOLO11 + EfficientNet-B0)")
    parser.add_argument('--image', type=str, default=None, help="Path to input coffee bean image")
    parser.add_argument('--yolo-path', type=str, default=None, help="Path to YOLO11 model weights (.pt)")
    parser.add_argument('--effnet-path', type=str, default=None, help="Path to EfficientNet model weights (.pth)")
    parser.add_argument('--conf', type=float, default=0.25, help="YOLO detection confidence threshold (default: 0.25)")
    parser.add_argument('--save-output', type=str, default=None, help="Path to save annotated output image")

    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # Fallback default image if none provided
    image_path = args.image
    if image_path is None:
        sample_candidate = os.path.join(project_root, "archive", "datasets", "DataCoffee_2022", "BigBroken", "0.00-0.05", "img", "BigBroken_20201015_723338_000-005_3,80g_122(1).jpg")
        if os.path.exists(sample_candidate):
            image_path = sample_candidate
        else:
            print("[ERROR] Please specify an input image using --image path/to/image.jpg")
            sys.exit(1)

    print("\n=======================================================")
    print("☕ Hybrid Coffee Bean Defect Classifier (YOLO11 + EfficientNet)")
    print("=======================================================")

    predictor = HybridCoffeePredictor(yolo_path=args.yolo_path, effnet_path=args.effnet_path)

    print(f"📷 Processing Image : {image_path}")
    print(f"🎯 Confidence Threshold: {args.conf * 100}%")
    print("=======================================================\n")

    results, annotated_img = predictor.predict(image_path, conf_threshold=args.conf)

    print(f"Detected {len(results)} individual coffee beans:\n")

    for bean in results:
        print(f"Bean {bean['bean_id']}:")
        print(f"  YOLO detection confidence: {bean['yolo_confidence']}%")
        print(f"  EfficientNet classification: {bean['effnet_classification']}")
        print(f"  Classification confidence: {bean['effnet_confidence']}%")
        print(f"  Final result: {bean['final_result']}\n")

    if args.save_output:
        save_path = os.path.abspath(args.save_output)
        cv2.imwrite(save_path, annotated_img)
        print(f"💾 Saved annotated image output to: {save_path}")

if __name__ == '__main__':
    main()
