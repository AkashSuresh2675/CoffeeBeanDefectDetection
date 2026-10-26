import os
import uuid
import cv2
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from ultralytics import YOLO

# ==============================================================================
# Flask Application Setup & Configuration
# ==============================================================================
app = Flask(__name__, static_folder=None)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

import sys
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from hybrid_model.hybrid_predict import HybridCoffeePredictor

# Configurable Model Paths
# Primary YOLO11 detector trained on 640-resolution with 9-class annotation scheme (BLACK, BROKEN, BROWN, BigBroken, IMMATURE, INSECT, MOLD, PartlyBlack, LIGHTFM_HEAVYFM)
DEFAULT_YOLO_PATH = os.path.join(PROJECT_ROOT, "hybrid_model", "models", "yolo11_stage2_best.pt")
if not os.path.exists(DEFAULT_YOLO_PATH):
    DEFAULT_YOLO_PATH = os.path.join(PROJECT_ROOT, "runs", "detect", "runs", "detect", "yolo11_stage2_640", "weights", "best.pt")
# Fallback to previous checkpoints if stage2 is not found
if not os.path.exists(DEFAULT_YOLO_PATH):
    DEFAULT_YOLO_PATH = os.path.join(PROJECT_ROOT, "runs", "detect", "runs", "detect", "yolo11_9class_corrected", "weights", "best.pt")
if not os.path.exists(DEFAULT_YOLO_PATH):
    DEFAULT_YOLO_PATH = os.path.join(PROJECT_ROOT, "runs", "detect", "train-5", "weights", "best.pt")
YOLO_MODEL_PATH = os.environ.get("YOLO_MODEL_PATH", DEFAULT_YOLO_PATH)

# Primary EfficientNet-B0 fine classifier trained on the 9-class classification dataset
DEFAULT_EFFNET_PATH = os.path.join(PROJECT_ROOT, "hybrid_model", "models", "efficientnet_improved_best.pth")
if not os.path.exists(DEFAULT_EFFNET_PATH):
    DEFAULT_EFFNET_PATH = os.path.join(PROJECT_ROOT, "hybrid_model", "models", "efficientnet_best.pth")
EFFNET_MODEL_PATH = os.environ.get("EFFNET_MODEL_PATH", DEFAULT_EFFNET_PATH)

# Uploads & Frontend Directories
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
FRONTEND_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Global Predictor Instance
hybrid_predictor = None

def load_models():
    global hybrid_predictor
    try:
        print(f"[INFO] Initializing HybridCoffeePredictor (YOLO11 + EfficientNet-B0)...")
        hybrid_predictor = HybridCoffeePredictor(yolo_path=YOLO_MODEL_PATH, effnet_path=EFFNET_MODEL_PATH)
    except Exception as e:
        print(f"[ERROR] Failed to initialize HybridCoffeePredictor: {e}")

load_models()

# ==============================================================================
# PIPELINE: YOLO11 Bounding Box Detection -> Crop Bean -> EfficientNet-B0 Classification
# ==============================================================================
def run_hybrid_pipeline(image_path, conf_threshold=0.25, iou_threshold=0.45, imgsz=640, effnet_conf_threshold=0.50):
    """
    Executes the 2-Stage Hybrid Coffee Bean Defect Detection Pipeline using HybridCoffeePredictor.
    - Detector: YOLO11 stage2 at 640 resolution (outputs yolo_class, confidence, bbox)
    - Classifier: EfficientNet-B0 fine defect classifier (outputs effnet_class, confidence, is_uncertain)
    """
    global hybrid_predictor
    if hybrid_predictor is None:
        load_models()

    raw_results, annotated_bgr = hybrid_predictor.predict(
        image_path,
        conf_threshold=conf_threshold,
        iou_threshold=iou_threshold,
        imgsz=imgsz,
        effnet_conf_threshold=effnet_conf_threshold
    )

    # Format detections payload for Flask API response
    formatted_detections = []
    for item in raw_results:
        formatted_detections.append({
            'id': item['bean_id'],
            'class': item['final_result'],
            'class_id': 0, # Resolved class string
            'confidence': item['confidence_score'],
            'confidence_percent': f"{item['effnet_confidence']}%",
            'effnet_class': item.get('effnet_classification', item['final_result']),
            'effnet_confidence': round(item['effnet_confidence'] / 100.0, 4),
            'yolo_confidence': round(item['yolo_confidence'] / 100.0, 4),
            'yolo_class': item['yolo_class'],
            'is_uncertain': item.get('is_uncertain', False),
            'bbox': item['bbox']
        })

    return formatted_detections, annotated_bgr

# ==============================================================================
# API Endpoints
# ==============================================================================
@app.route('/predict', methods=['POST'])
def predict():
    """
    POST /predict
    Receives image upload, detector confidence, and classifier confidence thresholds,
    runs the YOLO11 -> Crop -> EfficientNet-B0 hybrid pipeline, and returns JSON analysis results.
    """
    if 'file' not in request.files and 'image' not in request.files:
        return jsonify({'error': 'No image file provided in request'}), 400
    
    file = request.files.get('file') or request.files.get('image')
    if file.filename == '':
        return jsonify({'error': 'No image selected for uploading'}), 400

    # Save original uploaded image with unique filename
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']:
        ext = '.jpg'
    
    unique_id = uuid.uuid4().hex[:8]
    filename = f"upload_{unique_id}{ext}"
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(upload_path)

    if hybrid_predictor is None or hybrid_predictor.yolo_model is None:
        return jsonify({'error': 'Hybrid predictor model is not initialized properly'}), 500

    try:
        conf_threshold = float(request.form.get('confidence', 0.25))
        effnet_conf_threshold = float(request.form.get('effnet_confidence', 0.50))
        iou_threshold = float(request.form.get('iou', 0.45))
        imgsz = int(request.form.get('imgsz', 640))

        # Execute Hybrid Pipeline (YOLO11 Detection -> Crop -> EfficientNet Classification)
        detections, annotated_img_bgr = run_hybrid_pipeline(
            upload_path,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            imgsz=imgsz,
            effnet_conf_threshold=effnet_conf_threshold
        )

        # Save annotated image result
        annotated_filename = f"annotated_{unique_id}.jpg"
        annotated_path = os.path.join(app.config['UPLOAD_FOLDER'], annotated_filename)
        cv2.imwrite(annotated_path, annotated_img_bgr)

        # Calculate result card metrics
        class_counts = {}
        total_conf = 0.0
        for det in detections:
            c = det['class']
            class_counts[c] = class_counts.get(c, 0) + 1
            total_conf += det['confidence']

        avg_conf = round(total_conf / len(detections), 4) if len(detections) > 0 else 0.0

        response_payload = {
            'success': True,
            'total_detections': len(detections),
            'defect_categories_count': len(class_counts),
            'average_confidence': avg_conf,
            'average_confidence_percent': f"{round(avg_conf * 100, 1)}%",
            'class_counts': class_counts,
            'detections': detections,
            'annotated_image_url': f"/uploads/{annotated_filename}",
            'original_image_url': f"/uploads/{filename}",
            'pipeline_info': {
                'stage1': 'YOLO11 Object Detector (Bean Bounding Boxes)',
                'stage2': 'EfficientNet-B0 Classifier (Fine Defect Classification)',
                'architecture': 'YOLO11 + EfficientNet-B0 Hybrid Pipeline (Active)'
            }
        }
        return jsonify(response_payload)

    except Exception as e:
        print(f"[ERROR] Hybrid prediction error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f"Failed to process image: {str(e)}"}), 500

# ==============================================================================
# Static File Routes for Uploads & Frontend
# ==============================================================================
@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_FOLDER, 'index.html')

@app.route('/<path:filename>')
def serve_frontend_assets(filename):
    if os.path.exists(os.path.join(FRONTEND_FOLDER, filename)):
        return send_from_directory(FRONTEND_FOLDER, filename)
    return jsonify({'error': 'File not found'}), 404

# ==============================================================================
# Application Entry Point
# ==============================================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n=======================================================")
    print(f"☕ Coffee Bean Defect Detection Server Running!")
    print(f"🧬 Architecture: YOLO11 + EfficientNet-B0 Hybrid Pipeline")
    print(f"🔗 Local Web App URL: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    app.run(host='0.0.0.0', port=port, debug=True)
