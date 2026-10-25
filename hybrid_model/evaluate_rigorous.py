import os
import sys
import random
import csv
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
import numpy as np
from sklearn.metrics import (
    f1_score,
    accuracy_score,
    precision_score,
    recall_score,
    classification_report,
    confusion_matrix
)

# Set stdout encoding
sys.stdout.reconfigure(encoding='utf-8')

# Custom dataset wrapper
class TransformedCoffeeDataset(Dataset):
    def __init__(self, samples, transform=None):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, target = self.samples[idx]
        img = Image.open(path).convert('RGB')
        if self.transform is not None:
            img = self.transform(img)
        return img, target, path

def get_efficientnet_b0_model(num_classes):
    from torchvision.models import efficientnet_b0
    model = efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(project_root, "hybrid_model", "models", "efficientnet_improved_best.pth")
    data_dir = os.path.join(project_root, "archive", "datasets", "DataCoffee_2022")

    print("\n" + "="*70)
    print("[EVALUATION] RIGOROUS BENCHMARK EVALUATION OF EFFICIENTNET-B0 MODEL")
    print("="*70)
    print(f"Model Checkpoint : {model_path}")
    print(f"Dataset Root     : {data_dir}")
    print("="*70 + "\n")

    if not os.path.exists(model_path):
        print(f"[ERROR] Checkpoint not found at: {model_path}")
        sys.exit(1)

    # Load checkpoint
    checkpoint = torch.load(model_path, map_location='cpu')
    class_names = checkpoint.get('class_names')
    class_to_idx = checkpoint.get('class_to_idx')
    best_acc = checkpoint.get('best_val_acc')
    epoch = checkpoint.get('epoch')
    val_loss = checkpoint.get('val_loss')

    print(f"Checkpoint Metadata:")
    print(f"   * Epoch Saved       : {epoch}")
    print(f"   * Recorded Val Acc  : {best_acc:.2f}%")
    print(f"   * Recorded Val Loss : {val_loss:.6f}")
    print(f"   * Class Names ({len(class_names)}): {class_names}")
    print(f"   * Class to Index    : {class_to_idx}")
    print("-" * 70)

    # Collect clean dataset samples across the 9 classes
    all_clean_samples = []
    for c in class_names:
        class_folder = os.path.join(data_dir, c)
        if not os.path.exists(class_folder):
            continue
        for sub in sorted(os.listdir(class_folder)):
            img_sub = os.path.join(class_folder, sub, "img")
            if os.path.isdir(img_sub):
                for f in sorted(os.listdir(img_sub)):
                    if f.lower().endswith(('.jpg', '.jpeg', '.png')) and not f.startswith('.'):
                        full_p = os.path.join(img_sub, f)
                        all_clean_samples.append((full_p, class_to_idx[c]))

    print(f"[INFO] Discovered {len(all_clean_samples)} clean plate images across {len(class_names)} classes.")
    for c in class_names:
        count = sum(1 for p, t in all_clean_samples if t == class_to_idx[c])
        print(f"   * {c:<12}: {count} images")
    print("-" * 70)

    # Setup evaluation transforms
    imagenet_mean = [0.485, 0.456, 0.406]
    imagenet_std = [0.229, 0.224, 0.225]
    eval_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=imagenet_mean, std=imagenet_std)
    ])

    # Reconstruct the validation split used during training (train_efficientnet.py seed=42, val_split=0.2)
    random.seed(42)
    shuffled_samples = all_clean_samples.copy()
    random.shuffle(shuffled_samples)

    val_size = int(len(shuffled_samples) * 0.2) # 231 images
    val_samples = shuffled_samples[:val_size]
    train_samples = shuffled_samples[val_size:] # 928 images

    print(f"[INFO] Reconstructed Train/Val Split (seed=42, 80/20 ratio):")
    print(f"   * Training split   : {len(train_samples)} images")
    print(f"   * Validation split : {len(val_samples)} images")
    print("-" * 70)

    # Instantiate model
    model = get_efficientnet_b0_model(num_classes=len(class_names))
    model.load_state_dict(checkpoint['model_state_dict'])
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)
    model.eval()

    def evaluate_split(split_name, samples_list, csv_filename):
        dataset = TransformedCoffeeDataset(samples_list, transform=eval_transform)
        loader = DataLoader(dataset, batch_size=8, shuffle=False, num_workers=0)

        y_true = []
        y_pred = []
        image_paths = []
        pred_probs = []

        print(f"\n[INFERENCE] Running Inference on: {split_name} ({len(samples_list)} samples)...")
        with torch.no_grad():
            for imgs, targets, paths in loader:
                imgs = imgs.to(device)
                outputs = model(imgs)
                probs = torch.softmax(outputs, dim=1)
                confs, preds = torch.max(probs, 1)

                y_true.extend(targets.cpu().numpy().tolist())
                y_pred.extend(preds.cpu().numpy().tolist())
                image_paths.extend(paths)
                pred_probs.extend(confs.cpu().numpy().tolist())

        y_true = np.array(y_true)
        y_pred = np.array(y_pred)

        # Calculate metrics
        acc = accuracy_score(y_true, y_pred)
        macro_f1 = f1_score(y_true, y_pred, average="macro")
        macro_p = precision_score(y_true, y_pred, average="macro", zero_division=0)
        macro_r = recall_score(y_true, y_pred, average="macro", zero_division=0)
        weighted_f1 = f1_score(y_true, y_pred, average="weighted")
        per_class_f1 = f1_score(y_true, y_pred, average=None, zero_division=0)
        per_class_p = precision_score(y_true, y_pred, average=None, zero_division=0)
        per_class_r = recall_score(y_true, y_pred, average=None, zero_division=0)

        print("\n" + "="*70)
        print(f"[RESULTS] {split_name.upper()} RESULTS SUMMARY")
        print("="*70)
        print(f"Evaluated Samples  : {len(y_true)}")
        print(f"Accuracy           : {acc * 100:.2f}%")
        print(f"Macro-F1 Score     : {macro_f1:.4f} ({macro_f1 * 100:.2f}%)")
        print(f"Macro-Precision    : {macro_p:.4f} ({macro_p * 100:.2f}%)")
        print(f"Macro-Recall       : {macro_r:.4f} ({macro_r * 100:.2f}%)")
        print(f"Weighted-F1 Score  : {weighted_f1:.4f} ({weighted_f1 * 100:.2f}%)")
        print("-" * 70)
        print(f"{'Class Name':<14} | {'Support':<8} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10}")
        print("-" * 70)
        for i, c in enumerate(class_names):
            supp = int(np.sum(y_true == i))
            print(f"{c:<14} | {supp:<8} | {per_class_p[i]*100:8.2f}% | {per_class_r[i]*100:8.2f}% | {per_class_f1[i]*100:8.2f}%")
        print("-" * 70)

        # Save to CSV
        csv_path = os.path.join(project_root, csv_filename)
        with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "image_path",
                "filename",
                "true_label_idx",
                "true_label_name",
                "pred_label_idx",
                "pred_label_name",
                "pred_confidence",
                "is_correct"
            ])
            for p, yt, yp, conf in zip(image_paths, y_true, y_pred, pred_probs):
                writer.writerow([
                    p,
                    os.path.basename(p),
                    yt,
                    class_names[yt],
                    yp,
                    class_names[yp],
                    f"{conf:.4f}",
                    int(yt == yp)
                ])
        print(f"[CSV SAVED] Verification CSV saved to: {csv_path}")
        return {
            "accuracy": acc,
            "macro_f1": macro_f1,
            "macro_p": macro_p,
            "macro_r": macro_r,
            "weighted_f1": weighted_f1,
            "per_class_f1": {class_names[i]: float(per_class_f1[i]) for i in range(len(class_names))},
            "per_class_p": {class_names[i]: float(per_class_p[i]) for i in range(len(class_names))},
            "per_class_r": {class_names[i]: float(per_class_r[i]) for i in range(len(class_names))},
            "csv_path": csv_path,
            "num_evaluated": len(y_true)
        }

    # Evaluate on both the validation split and the full dataset
    val_metrics = evaluate_split("Validation Split (seed=42, 20%)", val_samples, "efficientnet_validation_predictions.csv")
    full_metrics = evaluate_split("Entire Dataset (1,159 Clean Images)", all_clean_samples, "efficientnet_full_dataset_predictions.csv")

    print("\n" + "="*70)
    print("[SUCCESS] EVALUATION AND METRIC CALCULATION COMPLETED SUCCESSFULLY!")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
