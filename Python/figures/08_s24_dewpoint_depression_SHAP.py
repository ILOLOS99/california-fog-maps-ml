import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# Set publication-quality style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_context("paper", font_scale=1.4)


datasets = {
    "LightGBM": {
        "path": "LightGBM_dewpoint_dep_beeswarm.csv",
        "color": "#378ADD",
        "label": "LightGBM — Test Stations",
    },
    "XGBoost": {
        "path": "XGBoost_dewpoint_dep_beeswarm.csv",
        "color": "#D85A30",
        "label": "XGBoost — Test Stations",
    },
}

FIGURE_LABELS = {
    "LightGBM": "8",
    "XGBoost": "S24",
}


# Plotting function
def plot_shap_scatter(df, model_name, color, label, output_stem):
    print(f"\n{'='*60}")
    print(f"Model: {model_name}")
    print(f"  Observations : {len(df):,}")
    print(f"  SHAP range   : [{df['shap_value'].min():.4f}, {df['shap_value'].max():.4f}]")
    print(f"  Feature range: [{df['feature_value'].min():.4f}, {df['feature_value'].max():.4f}]")
    print(f"  Fog events   : {df['fog_label'].sum()} ({100*df['fog_label'].mean():.1f}%)")

    # Boundary detection
    df_sorted = df.sort_values('feature_value')

    left_boundary = None
    for fv in df_sorted['feature_value'].unique():
        if (df[df['feature_value'] <= fv]['shap_value'] >= 0).all():
            left_boundary = fv
        else:
            break

    right_boundary = None
    for fv in df_sorted['feature_value'].unique()[::-1]:
        if (df[df['feature_value'] >= fv]['shap_value'] <= 0).all():
            right_boundary = fv
        else:
            break

    if left_boundary is not None:
        print(f"  Left boundary  (no neg. SHAP to left) : {left_boundary:.1f}°C")
    if right_boundary is not None:
        print(f"  Right boundary (no pos. SHAP to right): {right_boundary:.1f}°C")

    # Figure layout
    fig = plt.figure(figsize=(10, 7), dpi=300)
    gs  = fig.add_gridspec(4, 1, height_ratios=[1, 0.05, 5, 0.5], hspace=0)

    # Histogram (top)
    ax_hist = fig.add_subplot(gs[0])
    ax_hist.hist(df['feature_value'], bins=50, color=color, alpha=0.5, edgecolor='none')
    ax_hist.set_xlim(df['feature_value'].min(), df['feature_value'].max())
    ax_hist.set_xticks([])
    ax_hist.spines[['top', 'right', 'bottom']].set_visible(False)
    ax_hist.set_ylabel('n', fontsize=12, fontweight='bold')

    # Scatter (main)
    ax = fig.add_subplot(gs[2])
    ax.scatter(
        df['feature_value'], df['shap_value'],
        color=color, alpha=0.5, s=20,
        edgecolors='none', rasterized=True
    )
    ax.axhline(y=0, color='black', linestyle='--', linewidth=1.5, alpha=0.5, zorder=1)

    y_min, y_max = ax.get_ylim()
    y_range      = y_max - y_min
    label_y_bottom = y_min - 0.05 * y_range
    label_y_top    = y_max + 0.05 * y_range

    # Left boundary
    if left_boundary is not None:
        ax.plot([left_boundary, left_boundary], [y_min, label_y_top],
                color='red', linestyle='--', linewidth=2, alpha=0.7, zorder=2, clip_on=False)
        ax.text(left_boundary, label_y_top, f'{left_boundary:.1f}°C',
                ha='center', va='bottom', color='red', fontsize=11, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                          edgecolor='red', linewidth=1.5),
                clip_on=False)

    # Right boundary
    if right_boundary is not None:
        ax.plot([right_boundary, right_boundary], [y_max, label_y_bottom],
                color='red', linestyle='--', linewidth=2, alpha=0.7, zorder=2, clip_on=False)
        ax.text(right_boundary, label_y_bottom, f'{right_boundary:.1f}°C',
                ha='center', va='top', color='red', fontsize=11, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                          edgecolor='red', linewidth=1.5),
                clip_on=False)

    ax.set_xlabel('Dewpoint Depression (°C)', fontsize=14, fontweight='bold')
    ax.set_ylabel('SHAP Value (log-odds)',     fontsize=14, fontweight='bold')
    ax.set_xlim(df['feature_value'].min(), df['feature_value'].max())

    fig.suptitle(
        f'SHAP Scatter Plot: Impact of Dewpoint Depression on Fog Prediction\n{label}',
        fontsize=15, fontweight='bold', y=0.98
    )

    ax.text(0.98, 0.98, f'n = {len(df):,} observations',
            transform=ax.transAxes, fontsize=10,
            va='top', ha='right',
            bbox=dict(boxstyle='round', facecolor='wheat',
                      alpha=0.85, edgecolor='gray', linewidth=1.5))

    # Save
    fig.savefig(
        f"{output_stem}.png",
        dpi=300,
        bbox_inches="tight",
        facecolor="white"
    )

    plt.show()
    plt.close()

    print(f"  Saved: {output_stem}.png")

   
# Run for both models
for model_name, cfg in datasets.items():
    df = pd.read_csv(cfg["path"])
    fig_label = FIGURE_LABELS[model_name]
    output_stem = f"figure_{fig_label}"

    plot_shap_scatter(
        df,
        model_name,
        cfg["color"],
        cfg["label"],
        output_stem
    )
