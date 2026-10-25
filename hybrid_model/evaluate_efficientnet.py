import os
import sys
import argparse
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

def get_efficientnet_b0_model(num_classes):
    try:
        from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
        weights = None # We will load our trained weights
        model = efficientnet_b0(weights=weights)
    except (ImportError, AttributeError):
        from torchvision.models import efficientnet_b0
        model = efficientnet_b0(pretrained=False)

    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model

def main():
    parser = argparse.ArgumentParser(description="Evaluate Trained EfficientNet-B0 Model for Coffee Bean Defects")
    parser.add_argument('--model-path', type=str,
                        default=os.path.join("hybrid_model", "models", "efficientnet_improved_best.pth"),
                        help="Path to trained model checkpoint (.pth)")
    parser.add_argument('--data-dir', type=str,
                        default=os.path.join("archive", "datasets", "DataCoffee_2022"),
                        help="Path to dataset folder containing class subdirectories")
    parser.add_argument('--batch-size', type=int, default=4,
                        help="Batch size for evaluation (default: 4)")

    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    model_path = os.path.abspath(os.path.join(project_root, args.model_path)) if not os.path.isabs(args.model_path) else args.model_path
    data_dir = os.path.abspath(os.path.join(project_root, args.data_dir)) if not os.path.isabs(args.data_dir) else args.data_dir

    print("\n=======================================================")
    print("🔍 EfficientNet-B0 Model Evaluation")
    print("=======================================================")
    print(f"💾 Loading Checkpoint : {model_path}")
    print(f"📁 Evaluating Dataset : {data_dir}")
    print("=======================================================\n")

    if not os.path.exists(model_path):
        print(f"[ERROR] Trained model checkpoint not found at: '{model_path}'")
        print("Please run 'python hybrid_model/train_efficientnet.py' first to train and save the model.")
        sys.exit(1)

    if not os.path.exists(data_dir):
        print(f"[ERROR] Dataset directory not found at: '{data_dir}'")
        sys.exit(1)

    # Load checkpoint
    checkpoint = torch.load(model_path, map_location='cpu')
    class_names = checkpoint.get('class_names', None)
    
    if class_names is None:
        # Fallback to discovering classes from directory
        class_names = sorted([d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))])
        
    num_classes = len(class_names)

    # Initialize and load weights
    model = get_efficientnet_b0_model(num_classes=num_classes)
    model.load_state_dict(checkpoint['model_state_dict'])
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    model.eval()

    # Transforms (Validation ImageNet normalization)
    imagenet_mean = [0.485, 0.456, 0.406]
    imagenet_std = [0.229, 0.224, 0.225]

    eval_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=imagenet_mean, std=imagenet_std)
    ])

    eval_dataset = datasets.ImageFolder(root=data_dir, transform=eval_transform)
    eval_loader = DataLoader(eval_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)

    criterion = nn.CrossEntropyLoss()

    running_loss = 0.0
    correct_preds = 0
    total_samples = 0

    class_correct = {cls: 0 for cls in class_names}
    class_total = {cls: 0 for cls in class_names}

    with torch.no_grad():
        for images, labels in eval_loader:
            images, labels = images.to(device), labels.to(device)

            outputs = model(images)
            loss = criterion(outputs, labels)

            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)

            total_samples += labels.size(0)
            correct_preds += (preds == labels).sum().item()

            for label, pred in zip(labels, preds):
                cls_name = class_names[label.item()]
                if label.item() == pred.item():
                    class_correct[cls_name] += 1
                class_total[cls_name] += 1

    overall_loss = running_loss / total_samples if total_samples > 0 else 0.0
    overall_acc = (correct_preds / total_samples * 100.0) if total_samples > 0 else 0.0

    print("-----------------------------------------------------------------------------------")
    print(f"📊 EVALUATION SUMMARY")
    print("-----------------------------------------------------------------------------------")
    print(f"Total Evaluated Samples : {total_samples}")
    print(f"Overall Evaluation Loss : {overall_loss:.4f}")
    print(f"Overall Accuracy        : {overall_acc:.2f}%\n")

    print("🏷️  PER-CLASS ACCURACY BREAKDOWN:")
    print("-----------------------------------------------------------------------------------")
    for cls_name in class_names:
        tot = class_total[cls_name]
        corr = class_correct[cls_name]
        acc = (corr / tot * 100.0) if tot > 0 else 0.0
        print(f"   • {cls_name:<12} : {acc:6.2f}%  ({corr}/{tot} correct)")
    print("-----------------------------------------------------------------------------------\n")

if __name__ == '__main__':
    main()
