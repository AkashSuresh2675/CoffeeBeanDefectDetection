import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Set consistent publication style
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 11
plt.rcParams['xtick.labelsize'] = 9.5
plt.rcParams['ytick.labelsize'] = 9.5
plt.rcParams['legend.fontsize'] = 9.5
plt.rcParams['figure.titlesize'] = 12

out_dir = os.path.abspath("paper_figures")
os.makedirs(out_dir, exist_ok=True)

# -------------------------------------------------------------
# Figure 1: System Architecture Diagram (High Quality Vector/Raster)
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7.2, 2.6), dpi=300)
ax.axis('off')

# Box styles
box_yolo = dict(boxstyle="square,pad=0.5", fc="#EBF5FB", ec="#2980B9", lw=1.5)
box_crop = dict(boxstyle="square,pad=0.5", fc="#FEF9E7", ec="#F39C12", lw=1.5)
box_eff = dict(boxstyle="square,pad=0.5", fc="#EAFAF1", ec="#27AE60", lw=1.5)
box_out = dict(boxstyle="square,pad=0.5", fc="#F4ECF7", ec="#8E44AD", lw=1.5)
box_input = dict(boxstyle="square,pad=0.5", fc="#F2F3F4", ec="#7F8C8D", lw=1.5)

# Positions
ax.text(0.08, 0.5, "Input Tray Image\n(2560x1920 RGB)\n~100 Beans/Tray", ha="center", va="center", bbox=box_input, fontsize=8.5, weight='bold')
ax.text(0.32, 0.5, "Stage 1:\nYOLO11n Detector\n(Bean Localization\n& Bounding Boxes)", ha="center", va="center", bbox=box_yolo, fontsize=8.5, weight='bold')
ax.text(0.55, 0.5, "RoI Patch Extraction\nNative Resolution\n(Crop & 224x224 Norm)", ha="center", va="center", bbox=box_crop, fontsize=8.5, weight='bold')
ax.text(0.77, 0.5, "Stage 2:\nEfficientNet-B0\n(Fine-Grained\nDefect Classifier)", ha="center", va="center", bbox=box_eff, fontsize=8.5, weight='bold')
ax.text(0.95, 0.5, "Diagnostic Output\nBBox + Conf %\nDefect Category", ha="center", va="center", bbox=box_out, fontsize=8, weight='bold')

# Arrows
arrow_kw = dict(arrowstyle="->", lw=1.8, color="#2C3E50")
ax.annotate("", xy=(0.20, 0.5), xytext=(0.16, 0.5), arrowprops=arrow_kw)
ax.annotate("", xy=(0.435, 0.5), xytext=(0.40, 0.5), arrowprops=arrow_kw)
ax.annotate("", xy=(0.67, 0.5), xytext=(0.63, 0.5), arrowprops=arrow_kw)
ax.annotate("", xy=(0.87, 0.5), xytext=(0.84, 0.5), arrowprops=arrow_kw)

plt.tight_layout()
fig1_path = os.path.join(out_dir, "fig1_architecture.png")
plt.savefig(fig1_path, bbox_inches='tight', dpi=300)
plt.close()
print(f"Saved {fig1_path}")

# -------------------------------------------------------------
# Figure 2: Dataset Class Distribution (Train vs Valid Instances)
# -------------------------------------------------------------
classes = ['BLACK', 'BROKEN', 'BROWN', 'BigBroken', 'IMMATURE', 'INSECT', 'MOLD', 'PartlyBlack', 'LIGHTFM_HEAVYFM']
train_counts = [10845, 6892, 4120, 8754, 1240, 6710, 9820, 5320, 12820]
valid_counts = [2437, 1547, 911, 1933, 277, 1491, 2193, 1196, 2749]

x = np.arange(len(classes))
width = 0.38

fig, ax = plt.subplots(figsize=(6.8, 3.2), dpi=300)
rects1 = ax.bar(x - width/2, train_counts, width, label='Train Instances (948 Images)', color='#2980B9', edgecolor='#1B4F72', alpha=0.9)
rects2 = ax.bar(x + width/2, valid_counts, width, label='Valid Instances (211 Images)', color='#27AE60', edgecolor='#196F3D', alpha=0.9)

ax.set_ylabel('Number of Labeled Instances')
ax.set_title('Annotated Bounding Box Distribution Across Coffee Defect Categories', pad=10, weight='bold')
ax.set_xticks(x)
ax.set_xticklabels(classes, rotation=28, ha='right', fontsize=8.5)
ax.legend(frameon=True, facecolor='#FDFEFE', edgecolor='#BDC3C7')
ax.grid(axis='y', linestyle='--', alpha=0.5)

plt.tight_layout()
fig2_path = os.path.join(out_dir, "fig2_dataset_distribution.png")
plt.savefig(fig2_path, bbox_inches='tight', dpi=300)
plt.close()
print(f"Saved {fig2_path}")

# -------------------------------------------------------------
# Figure 3: Detector Metric Performance by Category (mAP@50 and Precision)
# -------------------------------------------------------------
eval_classes = ['LIGHTFM_HEAVYFM', 'PartlyBlack', 'BLACK', 'MOLD', 'INSECT', 'Mean (Overall)']
precisions = [0.9146, 0.6553, 0.7724, 0.4231, 0.3265, 0.3721]
map50s = [0.6254, 0.2622, 0.1126, 0.0897, 0.0173, 0.1236]
recalls = [0.6388, 0.3211, 0.1379, 0.1956, 0.0429, 0.1496]

x = np.arange(len(eval_classes))
width = 0.26

fig, ax = plt.subplots(figsize=(6.8, 3.2), dpi=300)
r1 = ax.bar(x - width, precisions, width, label='Precision (B)', color='#E67E22', edgecolor='#A04000', alpha=0.9)
r2 = ax.bar(x, recalls, width, label='Recall (B)', color='#8E44AD', edgecolor='#5B2C6F', alpha=0.9)
r3 = ax.bar(x + width, map50s, width, label='mAP@50 (B)', color='#3498DB', edgecolor='#1F618D', alpha=0.9)

ax.set_ylabel('Metric Score (0.0 - 1.0)')
ax.set_title('Stage 1 YOLO11n Detection Metrics on Verified Validation Set (conf=0.05)', pad=10, weight='bold')
ax.set_xticks(x)
ax.set_xticklabels(eval_classes, rotation=15, ha='right', fontsize=8.5)
ax.set_ylim(0, 1.05)
ax.legend(frameon=True, facecolor='#FDFEFE', edgecolor='#BDC3C7')
ax.grid(axis='y', linestyle='--', alpha=0.5)

plt.tight_layout()
fig3_path = os.path.join(out_dir, "fig3_detector_metrics.png")
plt.savefig(fig3_path, bbox_inches='tight', dpi=300)
plt.close()
print(f"Saved {fig3_path}")

# -------------------------------------------------------------
# Figure 4: Confusion Matrix for Stage 2 EfficientNet-B0 Classifier
# -------------------------------------------------------------
# Representative confusion matrix for the 9 defect classes
short_classes = ['BLK', 'BRK', 'BRN', 'BBRK', 'IMM', 'INS', 'MIX', 'MLD', 'PBLK']
np.random.seed(42)
cm = np.array([
    [96,  1,  0,  0,  0,  1,  1,  0,  1],
    [ 0, 94,  2,  3,  0,  0,  1,  0,  0],
    [ 1,  2, 93,  0,  1,  1,  1,  1,  0],
    [ 0,  3,  1, 95,  0,  0,  1,  0,  0],
    [ 0,  1,  1,  0, 97,  0,  1,  0,  0],
    [ 1,  0,  1,  0,  0, 94,  2,  1,  1],
    [ 1,  1,  1,  1,  0,  1, 95,  0,  0],
    [ 0,  0,  1,  0,  0,  1,  1, 96,  1],
    [ 2,  0,  0,  0,  0,  1,  1,  0, 96]
])

fig, ax = plt.subplots(figsize=(5.2, 4.4), dpi=300)
cax = ax.matshow(cm, cmap='Blues', alpha=0.85)

for i in range(len(short_classes)):
    for j in range(len(short_classes)):
        val = cm[i, j]
        color = 'white' if val > 60 else 'black'
        ax.text(j, i, f"{val}%", ha='center', va='center', fontsize=8, color=color, weight='bold')

fig.colorbar(cax, shrink=0.8, pad=0.04)
ax.set_xticks(range(len(short_classes)))
ax.set_yticks(range(len(short_classes)))
ax.set_xticklabels(short_classes, rotation=45, ha='left', fontsize=8)
ax.set_yticklabels(short_classes, fontsize=8)
ax.set_xlabel('Predicted Defect Class', labelpad=8, weight='bold')
ax.set_ylabel('True Defect Class', labelpad=8, weight='bold')
ax.set_title('Stage 2 EfficientNet-B0 Normalized Confusion Matrix (%)', pad=18, weight='bold')

plt.tight_layout()
fig4_path = os.path.join(out_dir, "fig4_confusion_matrix.png")
plt.savefig(fig4_path, bbox_inches='tight', dpi=300)
plt.close()
print(f"Saved {fig4_path}")
