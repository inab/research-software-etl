import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# Helvetica if available
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Helvetica", "Arial", "DejaVu Sans"]
plt.rcParams["mathtext.default"] = "regular"


def smoothstep(t):
    return 3 * t**2 - 2 * t**3


def draw_ribbon(ax, x0, x1, y0_low, y0_high, y1_low, y1_high,
                color, alpha=1.0, zorder=1, n=300):
    xs = np.linspace(x0, x1, n)
    t = (xs - x0) / (x1 - x0)
    s = smoothstep(t)

    y_low = y0_low + (y1_low - y0_low) * s
    y_high = y0_high + (y1_high - y0_high) * s

    ax.fill_between(xs, y_low, y_high, color=color, alpha=alpha, linewidth=0, zorder=zorder)


def draw_node(ax, x, y_center, height, width, color, rounding=0.03, zorder=5):
    rect = FancyBboxPatch(
        (x - width / 2, y_center - height / 2),
        width,
        height,
        boxstyle=f"round,pad=0,rounding_size={rounding}",
        linewidth=0,
        facecolor=color,
        zorder=zorder
    )
    ax.add_patch(rect)


# -------------------------
# Data
# -------------------------
initial = 1156
resolved_ai = 1049
unresolved_ai = 107
resolved_human = 88
still_unresolved = 19

# -------------------------
# Style
# -------------------------
bg = "white"
c_left = "#8a8fb8"
c_blue = "#d6eaff"
c_blue_node = "#2e88e8"
c_orange = "#fabbb1"
c_orange_node = "#f55a42"
c_yellow = "#fce9b6"
c_yellow_node = "#f0b82e"
c_green = "#cdddb7"
c_green_node = "#99c46d"
txt = "black"

# -------------------------
# Figure
# -------------------------
fig, ax = plt.subplots(figsize=(2.8, 2.15), dpi=300)
fig.patch.set_facecolor(bg)
ax.set_facecolor(bg)

# Horizontal positions
x_left = 0.30
x_mid = 1.72
x_right = 3.05

# -------------------------
# Scaling
# -------------------------
usable_height = 1.86
scale = usable_height / initial

# true ribbon heights
h_initial = initial * scale
h_ai = resolved_ai * scale
h_unresolved = unresolved_ai * scale
h_human = resolved_human * scale
h_still = still_unresolved * scale

# visible node heights
min_node_height = 0.045
h_initial_node = max(h_initial, min_node_height)
h_ai_node = max(h_ai, min_node_height)
h_unresolved_node = max(h_unresolved, min_node_height)
h_human_node = max(h_human, min_node_height)
h_still_node = max(h_still, min_node_height)

# -------------------------
# Vertical layout
# -------------------------
y_left_top = 1.92
y_left_bottom = y_left_top - h_initial

# left split for ribbons
y_left_ai_low = y_left_top - h_ai
y_left_ai_high = y_left_top
y_left_unres_low = y_left_bottom
y_left_unres_high = y_left_bottom + h_unresolved

# AI target ribbon
y_ai_top = 1.92
y_ai_bottom = y_ai_top - h_ai

# middle unresolved ribbon block
y_mid_top = 0.18
y_mid_bottom = y_mid_top - h_unresolved

# split at middle
y_mid_human_low = y_mid_top - h_human
y_mid_human_high = y_mid_top
y_mid_still_low = y_mid_bottom
y_mid_still_high = y_mid_bottom + h_still

# right targets with spacing
node_gap = 0.1

y_human_top = y_ai_bottom - node_gap
y_human_bottom = y_human_top - h_human

y_still_top = y_human_bottom - node_gap
y_still_bottom = y_still_top - h_still

# node centers use ribbon centers, but node heights are visually boosted
y_left_node_center = (y_left_top + y_left_bottom) / 2
y_mid_node_center = (y_mid_top + y_mid_bottom) / 2
y_ai_node_center = (y_ai_top + y_ai_bottom) / 2
y_human_node_center = (y_human_top + y_human_bottom) / 2
y_still_node_center = (y_still_top + y_still_bottom) / 2

# -------------------------
# Draw ribbons
# -------------------------
draw_ribbon(
    ax, x_left, x_right,
    y_left_ai_low, y_left_ai_high,
    y_ai_bottom, y_ai_top,
    color=c_blue, zorder=1
)

draw_ribbon(
    ax, x_left, x_mid,
    y_left_unres_low, y_left_unres_high,
    y_mid_bottom, y_mid_top,
    color=c_orange, zorder=2
)

draw_ribbon(
    ax, x_mid, x_right,
    y_mid_human_low, y_mid_human_high,
    y_human_bottom, y_human_top,
    color=c_yellow, zorder=3
)

draw_ribbon(
    ax, x_mid, x_right,
    y_mid_still_low, y_mid_still_high,
    y_still_bottom, y_still_top,
    color=c_green, zorder=4
)

# -------------------------
# Draw nodes
# -------------------------
node_w_left = 0.05
node_w = 0.045

draw_node(ax, x_left - 0.015, y_left_node_center,
          h_initial_node, node_w_left, c_left, rounding=0.02)

draw_node(ax, x_mid, y_mid_node_center,
          h_unresolved_node, node_w, c_orange_node, rounding=0.02)

draw_node(ax, x_right + 0.015, y_ai_node_center,
          h_ai_node, node_w, c_blue_node, rounding=0.02)

draw_node(ax, x_right + 0.015, y_human_node_center,
          h_human_node, node_w, c_yellow_node, rounding=0.02)

draw_node(ax, x_right + 0.015, y_still_node_center,
          h_still_node, node_w, c_green_node, rounding=0.02)

# -------------------------
# Labels
# -------------------------
common_text = dict(color=txt, linespacing=1.18)

# left label
ax.text(
    x_left + 0.09, y_left_node_center + 0.01,
    f"Initial conflict set\n$\\mathbf{{({initial:,})}}$",
    ha="left", va="center", fontsize=5, **common_text
)

# middle label
ax.text(
    x_mid + 0.07, y_mid_node_center + 0.00,
    f"AI-escalated\n$\\mathbf{{({unresolved_ai})}}$",
    ha="left",
    va="center",
    fontsize=5,
    zorder=20,
    **common_text,
)

# right-side labels placed to the right of the nodes
label_dx = 0.08
x_right_label = x_right + 0.015 + node_w / 2 + label_dx

ax.text(
    x_right_label, y_ai_node_center,
    f"AI-resolved\n$\\mathbf{{({resolved_ai:,})}}$",
    ha="left", va="center", fontsize=5, **common_text
)

ax.text(
    x_right_label, y_human_node_center,
    f"Human-resolved\n$\\mathbf{{({resolved_human})}}$",
    ha="left", va="center", fontsize=5, **common_text
)

ax.text(
    x_right_label, y_still_node_center,
    f"Still unresolved\n$\\mathbf{{({still_unresolved})}}$",
    ha="left", va="center", fontsize=5, **common_text
)

# -------------------------
# Final layout
# -------------------------
bottom_padding = 0.10
top_padding = 0.03

lowest_visible = min(
    y_left_node_center - h_initial_node / 2,
    y_human_node_center - h_human_node / 2,
    y_still_node_center - h_still_node / 2,
)

highest_visible = max(
    y_left_node_center + h_initial_node / 2,
    y_ai_node_center + h_ai_node / 2,
)

ax.set_xlim(0.05, 3.75)
ax.set_ylim(lowest_visible - bottom_padding, highest_visible + top_padding)
ax.axis("off")

plt.tight_layout(pad=0.08)

plt.savefig(
    "scripts/figures/pairwise_sankey_right_labels.png",
    dpi=300,
    bbox_inches="tight",
    facecolor="white"
)
