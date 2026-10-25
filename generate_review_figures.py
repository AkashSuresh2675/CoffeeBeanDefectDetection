import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

os.makedirs('review_figures', exist_ok=True)

# Set global styles
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.linewidth'] = 1.0

# ----------------------------------------------------
# FIG 1: Study Selection Flow Diagram (PRISMA-style)
# ----------------------------------------------------
fig, ax = plt.subplots(figsize=(8.5, 6.5), dpi=300)
ax.axis('off')

# Box styles
box_id = dict(boxstyle="round,pad=0.5", fc="#EBF5FB", ec="#2980B9", lw=1.5)
box_scr = dict(boxstyle="round,pad=0.5", fc="#FEF9E7", ec="#F39C12", lw=1.5)
box_elg = dict(boxstyle="round,pad=0.5", fc="#E8F8F5", ec="#16A085", lw=1.5)
box_inc = dict(boxstyle="round,pad=0.6", fc="#EAFAF1", ec="#27AE60", lw=2.0)
box_exc = dict(boxstyle="round,pad=0.5", fc="#FDEDEC", ec="#C0392B", lw=1.5)

# Identification
ax.text(0.3, 0.90, "Databases Queried (2018–2025):\n• IEEE Xplore: n = 142\n• Scopus: n = 188\n• ScienceDirect: n = 124\n• Web of Science: n = 106\nTotal Records Identified: N = 560", 
        ha="center", va="center", bbox=box_id, fontsize=9.5)

# Duplicate Removal
ax.annotate('', xy=(0.3, 0.77), xytext=(0.3, 0.81), arrowprops=dict(facecolor='#2C3E50', width=1.5, headwidth=6))
ax.text(0.3, 0.73, "Duplicates Removed\n(n = 168)\nRecords Screened: n = 392", ha="center", va="center", bbox=box_scr, fontsize=9.5)

# Screening Exclusions
ax.annotate('', xy=(0.65, 0.73), xytext=(0.46, 0.73), arrowprops=dict(facecolor='#C0392B', width=1.5, headwidth=6))
ax.text(0.78, 0.73, "Excluded at Screening (n = 238):\n• Non-coffee agriculture (n = 112)\n• Non-vision/chemical only (n = 74)\n• Non-peer-reviewed/abstracts (n = 52)", 
        ha="center", va="center", bbox=box_exc, fontsize=8.5)

# Eligibility
ax.annotate('', xy=(0.3, 0.58), xytext=(0.3, 0.67), arrowprops=dict(facecolor='#2C3E50', width=1.5, headwidth=6))
ax.text(0.3, 0.52, "Full-Text Articles Assessed\nfor Eligibility (n = 154)", ha="center", va="center", bbox=box_elg, fontsize=9.5)

# Full-text Exclusions
ax.annotate('', xy=(0.65, 0.52), xytext=(0.46, 0.52), arrowprops=dict(facecolor='#C0392B', width=1.5, headwidth=6))
ax.text(0.78, 0.52, "Excluded with Reasons (n = 96):\n• Insufficient metrics/validation (n = 38)\n• Roast grading only without defects (n = 32)\n• Hardware design without DL specs (n = 26)", 
        ha="center", va="center", bbox=box_exc, fontsize=8.5)

# Included
ax.annotate('', xy=(0.3, 0.38), xytext=(0.3, 0.46), arrowprops=dict(facecolor='#2C3E50', width=1.5, headwidth=6))
ax.text(0.3, 0.28, "Studies Included in Synthesis (N = 58):\n• Traditional ML & Handcrafted Vision (n = 12)\n• Standard Single-Stage CNN / YOLO (n = 22)\n• Two-Stage / Hybrid Detection-Classification (n = 14)\n• Spectral & Multimodal Sensory Systems (n = 10)", 
        ha="center", va="center", bbox=box_inc, fontsize=9.5, fontweight='bold')

plt.title("Fig. 1. Systematic Study-Selection Flow Diagram (PRISMA Compliant)", fontsize=11, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig("review_figures/fig1_study_selection.png", dpi=300)
plt.close()

# ----------------------------------------------------
# FIG 2: Taxonomy of Coffee Bean Defect Detection
# ----------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
ax.axis('off')

# Root
root_box = dict(boxstyle="square,pad=0.6", fc="#2C3E50", ec="black", lw=1.5)
ax.text(0.5, 0.92, "Computer Vision & ML Paradigms for Coffee Bean Defect Assessment", 
        ha="center", va="center", bbox=root_box, color="white", fontsize=11, fontweight='bold')

# Categories
cats = [
    ("1. Classical Vision &\nShallow ML", 0.14, "#3498DB", 
     "• Features: Color (HSV, Lab), GLCM, Shape\n• Classifiers: SVM, Random Forest, ANN\n• Pros: Low compute, interpretable\n• Cons: Poor generalization, manual tuning"),
    ("2. End-to-End Deep\nObject Detectors", 0.38, "#E67E22", 
     "• Architectures: Faster R-CNN, SSD, YOLOv5-v11\n• Single inference for localizing & classifying\n• Pros: Real-time, handles dense arrangements\n• Cons: Class imbalance across rare defect types"),
    ("3. Hierarchical &\nTwo-Stage Hybrids", 0.62, "#9B59B6", 
     "• Pipeline: Detection/Cropping + Fine Classifier\n• Models: YOLO11 + EfficientNet / ResNet / ViT\n• Pros: SOTA accuracy, decoupling localization\n• Cons: Modest increase in pipeline latency"),
    ("4. Spectral & Non-Destructive\nSensory Systems", 0.86, "#1ABC9C", 
     "• Modalities: HSI (400-1000nm), NIR, X-ray CT\n• Chemometrics: PLS-DA, Spectral 3D-CNN\n• Pros: Detects internal / chemical decay\n• Cons: Expensive hardware, high latency")
]

for title, x_pos, col, desc in cats:
    # Arrow from root
    ax.annotate('', xy=(x_pos, 0.78), xytext=(0.5, 0.86), 
                arrowprops=dict(facecolor='#7F8C8D', edgecolor='#7F8C8D', width=1.2, headwidth=5))
    # Category Header Box
    hdr_box = dict(boxstyle="round,pad=0.4", fc=col, ec="black", lw=1.2)
    ax.text(x_pos, 0.74, title, ha="center", va="center", bbox=hdr_box, color="white", fontsize=9.5, fontweight='bold')
    
    # Details Box
    dtl_box = dict(boxstyle="square,pad=0.5", fc="#F8F9F9", ec=col, lw=1.2)
    ax.text(x_pos, 0.45, desc, ha="center", va="center", bbox=dtl_box, fontsize=8.2, linespacing=1.3)

plt.title("Fig. 2. Taxonomy of Automated Coffee Bean Defect Detection and Quality Inspection Frameworks", fontsize=11, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig("review_figures/fig2_taxonomy.png", dpi=300)
plt.close()

# ----------------------------------------------------
# FIG 3: Comparative Synthesis & Research Roadmap
# ----------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)

methods = ['Classical ML (SVM/GLCM)', 'Single-Stage YOLOv5/v8', 'YOLO11 Detector Only', 'Hybrid YOLO11 + EfficientNet', 'HSI / NIR Chemometrics']
mAP_scores = [76.4, 88.2, 92.5, 96.8, 91.2]
fps_rates = [12, 65, 78, 48, 4]
bubble_sizes = [150, 400, 450, 650, 300]
colors = ['#3498DB', '#E67E22', '#F39C12', '#27AE60', '#9B59B6']

scatter = ax.scatter(fps_rates, mAP_scores, s=bubble_sizes, c=colors, alpha=0.75, edgecolors="black", linewidth=1.5)

for i, txt in enumerate(methods):
    offset_x = 2 if i != 3 else -12
    offset_y = 1.2 if i != 2 else -2.2
    ax.annotate(txt, (fps_rates[i] + offset_x, mAP_scores[i] + offset_y), fontsize=9, fontweight='bold', color="#1B2631")

ax.axhline(90, color='gray', linestyle='--', alpha=0.5, label='High-Accuracy Industrial Threshold (90% mAP)')
ax.axvline(30, color='red', linestyle='--', alpha=0.5, label='Real-Time Conveyor Sorting Threshold (30 FPS)')

ax.set_xlabel("Processing Speed (Frames Per Second - FPS)", fontsize=10, fontweight='bold')
ax.set_ylabel("Defect Classification mAP / Accuracy (%)", fontsize=10, fontweight='bold')
ax.set_title("Fig. 3. Comparative Synthesis: Accuracy vs. Real-Time Throughput across Paradigms", fontsize=11, fontweight='bold', pad=12)
ax.set_xlim(0, 95)
ax.set_ylim(70, 102)
ax.grid(True, linestyle=":", alpha=0.6)
ax.legend(loc="lower right", fontsize=8.5)

plt.tight_layout()
plt.savefig("review_figures/fig3_synthesis_roadmap.png", dpi=300)
plt.close()

print("Figures successfully generated in review_figures/")
