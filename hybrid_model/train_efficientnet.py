import os
import sys
import time
import argparse
import random
import json
from PIL import Image

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import datasets, transforms

# Custom Dataset wrapper to allow distinct train/val transforms on split samples
class TransformedCoffeeDataset(Dataset):
    def __init__(self, samples, transform=None):
        """
        samples: List of (image_path, target_class_idx) tuples
        transform: torchvision transforms pipeline
        """
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, target = self.samples[idx]
        try:
            img = Image.open(path).convert('RGB')
        except Exception as e:
            raise RuntimeError(f"Error loading image '{path}': {e}")
            
        if self.transform is not None:
            img = self.transform(img)
        return img, target

def get_efficientnet_b0_model(num_classes):
    """
    Load EfficientNet-B0 with ImageNet weights and update classifier for num_classes.
    """
    try:
        from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
        weights = EfficientNet_B0_Weights.DEFAULT
        model = efficientnet_b0(weights=weights)
        print("[INFO] Loaded EfficientNet-B0 with default ImageNet weights (torchvision v2 API).")
    except (ImportError, AttributeError):
        from torchvision.models import efficientnet_b0
        model = efficientnet_b0(pretrained=True)
        print("[INFO] Loaded EfficientNet-B0 with pretrained=True (torchvision v1 API).")

    # Replace classifier head for 9 coffee defect classes
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model

def main():
    parser = argparse.ArgumentParser(description="Train EfficientNet-B0 for Coffee Bean Defect Detection")
    parser.add_argument('--data-dir', type=str, 
                        default=os.path.join("archive", "datasets", "DataCoffee_2022"),
                        help="Path to dataset root folder containing class subdirectories")
    parser.add_argument('--output-model', type=str,
                        default=os.path.join("hybrid_model", "models", "efficientnet_improved_best.pth"),
                        help="Path to save the best model weights checkpoint")
    parser.add_argument('--epochs', type=int, default=15,
                        help="Number of training epochs (default: 15)")
    parser.add_argument('--batch-size', type=int, default=4,
                        help="Batch size for training and validation (default: 4)")
    parser.add_argument('--lr', type=float, default=0.0005,
                        help="Learning rate for Adam optimizer (default: 0.0005)")
    parser.add_argument('--val-split', type=float, default=0.2,
                        help="Validation split ratio (default: 0.2 for 80/20 split)")
    parser.add_argument('--seed', type=int, default=42,
                        help="Random seed for dataset split reproducibility")
    
    args = parser.parse_args()

    # Absolute path resolution
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_dir = os.path.abspath(os.path.join(project_root, args.data_dir)) if not os.path.isabs(args.data_dir) else args.data_dir
    output_model_path = os.path.abspath(os.path.join(project_root, args.output_model)) if not os.path.isabs(args.output_model) else args.output_model

    print("\n=======================================================")
    print("☕ EfficientNet-B0 Coffee Bean Defect Classifier")
    print("=======================================================")
    print(f"📁 Dataset Directory : {data_dir}")
    print(f"💾 Model Output Path  : {output_model_path}")
    print(f"🔄 Epochs             : {args.epochs}")
    print(f"📦 Batch Size         : {args.batch_size}")
    print(f"⚡ Learning Rate       : {args.lr}")
    print(f"📊 Validation Split    : {args.val_split * 100}%")
    print("=======================================================\n")

    if not os.path.exists(data_dir):
        print(f"[ERROR] Dataset directory not found: '{data_dir}'")
        sys.exit(1)

    # Set random seed
    random.seed(args.seed)
    torch.manual_seed(args.seed)

    # Load dataset index using ImageFolder to read classes
    full_folder_dataset = datasets.ImageFolder(root=data_dir)
    class_names = full_folder_dataset.classes
    class_to_idx = full_folder_dataset.class_to_idx
    num_classes = len(class_names)
    all_samples = full_folder_dataset.samples # list of (path, class_index)

    print(f"[INFO] Discovered {len(all_samples)} total images across {num_classes} classes:")
    for idx, cls_name in enumerate(class_names):
        count = sum(1 for _, target in all_samples if target == idx)
        print(f"   • {cls_name}: {count} images")
    print()

    # Train / Validation Split (80/20)
    samples_by_idx = all_samples.copy()
    random.shuffle(samples_by_idx)

    val_size = int(len(samples_by_idx) * args.val_split)
    val_samples = samples_by_idx[:val_size]
    train_samples = samples_by_idx[val_size:]

    # Data Transformations
    # ImageNet normalization standard values
    imagenet_mean = [0.485, 0.456, 0.406]
    imagenet_std = [0.229, 0.224, 0.225]

    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=15),
        transforms.ToTensor(),
        transforms.Normalize(mean=imagenet_mean, std=imagenet_std)
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=imagenet_mean, std=imagenet_std)
    ])

    train_dataset = TransformedCoffeeDataset(train_samples, transform=train_transform)
    val_dataset = TransformedCoffeeDataset(val_samples, transform=val_transform)

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)

    print(f"[INFO] Train set: {len(train_dataset)} images | Validation set: {len(val_dataset)} images")

    # Select Device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"[INFO] Operating Device: {device}")

    # Initialize Model, Loss, Optimizer
    model = get_efficientnet_b0_model(num_classes=num_classes)
    model = model.to(device)

    # --- Class-weighted CrossEntropyLoss to handle class imbalance ---
    # Count samples per class in the TRAINING split only
    train_class_counts = [0] * num_classes
    for _, label_idx in train_samples:
        train_class_counts[label_idx] += 1
    total_train_samples = sum(train_class_counts)
    # Weight = total / (num_classes * count_for_class)  -- inverse-frequency weighting
    class_weights = [
        total_train_samples / (num_classes * max(count, 1))
        for count in train_class_counts
    ]
    class_weights_tensor = torch.tensor(class_weights, dtype=torch.float).to(device)
    print("[INFO] Class weights for weighted CrossEntropyLoss:")
    for i, cls in enumerate(class_names):
        print(f"   • {cls}: count={train_class_counts[i]}, weight={class_weights[i]:.4f}")
    print()

    criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
    optimizer = optim.Adam(model.parameters(), lr=args.lr)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_model_path), exist_ok=True)

    best_val_acc = 0.0
    start_time = time.time()

    print("\n🚀 Starting EfficientNet-B0 Training Loop...")
    print("-----------------------------------------------------------------------------------")

    for epoch in range(1, args.epochs + 1):
        # Training Phase
        model.train()
        running_train_loss = 0.0
        correct_train = 0
        total_train = 0

        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_train_loss += loss.item() * images.size(0)
            _, predicted = torch.max(outputs, 1)
            total_train += labels.size(0)
            correct_train += (predicted == labels).sum().item()

        epoch_train_loss = running_train_loss / total_train if total_train > 0 else 0.0
        epoch_train_acc = (correct_train / total_train * 100.0) if total_train > 0 else 0.0

        # Validation Phase
        model.eval()
        running_val_loss = 0.0
        correct_val = 0
        total_val = 0
        # Per-class tracking for last-epoch report
        class_correct = [0] * num_classes
        class_total   = [0] * num_classes

        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)

                outputs = model(images)
                loss = criterion(outputs, labels)

                running_val_loss += loss.item() * images.size(0)
                _, predicted = torch.max(outputs, 1)
                total_val += labels.size(0)
                correct_val += (predicted == labels).sum().item()

                # Accumulate per-class stats
                for t, p in zip(labels.view(-1), predicted.view(-1)):
                    class_total[t.item()]   += 1
                    class_correct[t.item()] += int(t == p)

        epoch_val_loss = running_val_loss / total_val if total_val > 0 else 0.0
        epoch_val_acc = (correct_val / total_val * 100.0) if total_val > 0 else 0.0

        # Print per-epoch metrics strictly as required
        print(f"Epoch [{epoch:02d}/{args.epochs:02d}] | "
              f"Train Loss: {epoch_train_loss:.4f} | Train Acc: {epoch_train_acc:.2f}% | "
              f"Val Loss: {epoch_val_loss:.4f} | Val Acc: {epoch_val_acc:.2f}%")

        # Checkpoint Best Model
        if epoch_val_acc > best_val_acc:
            best_val_acc = epoch_val_acc
            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'class_names': class_names,
                'class_to_idx': class_to_idx,
                'best_val_acc': best_val_acc,
                'val_loss': epoch_val_loss,
                'optimizer_state_dict': optimizer.state_dict()
            }
            torch.save(checkpoint, output_model_path)
            print(f"   └── ⭐ Saved new best model checkpoint (Val Acc: {best_val_acc:.2f}%) to {output_model_path}")

    total_time = time.time() - start_time
    print("-----------------------------------------------------------------------------------")
    print(f"✅ Training completed in {total_time/60:.2f} minutes.")
    print(f"🏆 Best Validation Accuracy Achieved: {best_val_acc:.2f}%")
    print(f"💾 Checkpoint saved at: {output_model_path}")

    # --- Per-class validation accuracy (from last epoch's stats) ---
    print("\n📊 Per-Class Validation Accuracy (Last Epoch):")
    print("-" * 45)
    for i, cls_name in enumerate(class_names):
        if class_total[i] > 0:
            acc = 100.0 * class_correct[i] / class_total[i]
            print(f"   {cls_name:<12}: {class_correct[i]:>3}/{class_total[i]:>3} = {acc:6.2f}%")
        else:
            print(f"   {cls_name:<12}: no samples in validation set")
    print("-" * 45 + "\n")

if __name__ == '__main__':
    main()
