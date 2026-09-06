"""Courbes PNG génériques pour les rapports Markdown."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def _setup_matplotlib():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.dates import DateFormatter, AutoDateLocator

    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.edgecolor": "#D4E0DC",
            "axes.labelcolor": "#1A3D38",
            "xtick.color": "#7D8B96",
            "ytick.color": "#7D8B96",
            "text.color": "#1A3D38",
            "figure.facecolor": "#FFFFFF",
            "axes.facecolor": "#FFFFFF",
        }
    )
    return plt, DateFormatter, AutoDateLocator


def plot_line(
    points: list[tuple[datetime, float]],
    out_path: Path,
    *,
    title: str,
    ylabel: str,
    color: str = "#1A7A60",
    ref_low: float | None = None,
    ref_high: float | None = None,
) -> Path | None:
    if len(points) < 2:
        return None
    plt, DateFormatter, AutoDateLocator = _setup_matplotlib()
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    fig, ax = plt.subplots(figsize=(9.2, 3.6), dpi=140)
    ax.plot(xs, ys, color=color, linewidth=2.2, marker="o", markersize=4)
    ax.fill_between(xs, ys, color=color, alpha=0.12)
    if ref_low is not None and ref_high is not None:
        ax.axhspan(ref_low, ref_high, color="#3B82F6", alpha=0.08, zorder=0)
        ax.axhline(ref_low, color="#3B82F6", linewidth=0.8, linestyle="--", alpha=0.6)
        ax.axhline(ref_high, color="#3B82F6", linewidth=0.8, linestyle="--", alpha=0.6)
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", pad=10)
    ax.set_ylabel(ylabel)
    ax.xaxis.set_major_locator(AutoDateLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%y"))
    ax.grid(axis="y", color="#1A7A60", alpha=0.08)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_step_dose(
    points: list[tuple[datetime, float]],
    out_path: Path,
    *,
    title: str,
    ylabel: str,
    color: str = "#1A7A60",
) -> Path | None:
    if len(points) < 1:
        return None
    plt, DateFormatter, AutoDateLocator = _setup_matplotlib()
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    fig, ax = plt.subplots(figsize=(9.2, 3.6), dpi=140)
    ax.step(xs, ys, where="post", color=color, linewidth=2.2)
    ax.scatter(xs, ys, color=color, s=18, zorder=3)
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", pad=10)
    ax.set_ylabel(ylabel)
    ax.xaxis.set_major_locator(AutoDateLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%y"))
    ax.grid(axis="y", color="#1A7A60", alpha=0.08)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path
