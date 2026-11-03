"""Generates publication-quality charts for the FYP Thesis Report.

Outputs saved to reports/figures/:
  1. carbon_comparison_bar.png - Total Carbon Emissions & Savings %
  2. latency_cdf_curve.png - Cumulative Distribution Function of Response Time with SLA threshold
  3. pareto_tradeoff_scatter.png - Carbon vs. Latency Pareto Frontier
  4. regional_traffic_distribution.png - Cloud Region Traffic Allocation %
  5. sla_compliance_bar.png - SLA Compliance & Breach Analysis
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg") # Non-interactive backend for headless plotting
import matplotlib.pyplot as plt

FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Styling palette
PALETTE = {
    "Latency-First": "#3B82F6",    # Blue
    "Round-Robin": "#F59E0B",      # Amber / Orange
    "EcoSyn-Balanced": "#10B981",  # Emerald Green
    "EcoSyn-Green": "#047857",     # Dark Green
}


def plot_carbon_comparison(summary_df: pd.DataFrame) -> None:
    """Figure 1: Bar chart of Total Carbon Emissions with savings %."""
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)

    policies = summary_df["policy_label"].tolist()
    carbons = summary_df["total_carbon_g"].tolist()
    colors = [PALETTE.get(p, "#6B7280") for p in policies]

    bars = ax.bar(policies, carbons, color=colors, width=0.55, edgecolor="#1F2937", linewidth=1.2)
    ax.set_ylabel("Total Carbon Emissions ($gCO_2eq$)", fontsize=11, fontweight="bold")
    ax.set_title("Total Operational Carbon Emissions by Routing Policy\n(1,000 Invocations Workload)", fontsize=13, fontweight="bold", pad=15)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    # Add text labels on top of bars
    baseline_val = carbons[0]
    for idx, bar in enumerate(bars):
        height = bar.get_height()
        if idx == 0:
            label_text = f"{height:.4f} g\n[Baseline]"
        else:
            saved_pct = summary_df.iloc[idx].get("carbon_saved_pct", 0.0)
            label_text = f"{height:.4f} g\n(-{saved_pct:.1f}%)"
        ax.annotate(
            label_text,
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    ax.set_ylim(0, max(carbons) * 1.25)
    plt.tight_layout()
    output_path = FIGURES_DIR / "carbon_comparison_bar.png"
    plt.savefig(output_path)
    plt.close()
    print(f"Generated: {output_path}")


def plot_latency_cdf(raw_df: pd.DataFrame, sla_ms: float = 250.0) -> None:
    """Figure 2: Cumulative Distribution Function (CDF) of Response Times."""
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)

    policies = raw_df["policy"].unique()
    for policy in policies:
        sub = raw_df[raw_df["policy"] == policy]
        sorted_latencies = np.sort(sub["latency_ms"].values)
        cdf = np.arange(1, len(sorted_latencies) + 1) / len(sorted_latencies)
        ax.plot(
            sorted_latencies,
            cdf,
            label=policy,
            color=PALETTE.get(policy, "#6B7280"),
            linewidth=2.2,
        )

    # Draw SLA vertical reference line
    ax.axvline(
        x=sla_ms,
        color="#EF4444",
        linestyle="--",
        linewidth=1.8,
        label=f"SLA Target ({sla_ms:.0f} ms)",
    )

    ax.set_xlabel("End-to-End Response Time (ms)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Cumulative Probability (CDF)", fontsize=11, fontweight="bold")
    ax.set_title("Response Time CDF & SLA Boundary Compliance", fontsize=13, fontweight="bold", pad=15)
    ax.set_xlim(0, max(raw_df["latency_ms"].max() * 1.05, sla_ms * 1.3))
    ax.set_ylim(0, 1.05)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="lower right", frameon=True, fontsize=9.5)

    plt.tight_layout()
    output_path = FIGURES_DIR / "latency_cdf_curve.png"
    plt.savefig(output_path)
    plt.close()
    print(f"Generated: {output_path}")


def plot_pareto_tradeoff(summary_df: pd.DataFrame) -> None:
    """Figure 3: Carbon vs. Latency Pareto Frontier."""
    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=300)

    for _, row in summary_df.iterrows():
        policy = row["policy_label"]
        lat = row["avg_latency_ms"]
        carb = row["total_carbon_g"]
        color = PALETTE.get(policy, "#6B7280")

        ax.scatter(lat, carb, color=color, s=220, edgecolors="#111827", linewidth=1.5, zorder=5)
        ax.annotate(
            policy,
            xy=(lat, carb),
            xytext=(10, 8),
            textcoords="offset points",
            fontsize=9.5,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=color, lw=1.2, alpha=0.9),
        )

    ax.set_xlabel("Average Response Time (ms)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Total Carbon Emissions ($gCO_2eq$)", fontsize=11, fontweight="bold")
    ax.set_title("Carbon vs. Latency Pareto Frontier Trade-Off", fontsize=13, fontweight="bold", pad=15)
    ax.grid(True, linestyle="--", alpha=0.5)

    # Invert y-axis or annotate optimal corner
    ax.annotate(
        "Optimal Region\n(Low Latency, Low Carbon)",
        xy=(summary_df["avg_latency_ms"].min() * 0.95, summary_df["total_carbon_g"].min() * 1.05),
        xytext=(0, -35),
        textcoords="offset points",
        fontsize=8.5,
        color="#047857",
        fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#047857", lw=1.5),
    )

    plt.tight_layout()
    output_path = FIGURES_DIR / "pareto_tradeoff_scatter.png"
    plt.savefig(output_path)
    plt.close()
    print(f"Generated: {output_path}")


def plot_regional_traffic(raw_df: pd.DataFrame) -> None:
    """Figure 4: Regional traffic distribution across cloud regions."""
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)

    crosstab = pd.crosstab(raw_df["policy"], raw_df["selected_region"], normalize="index") * 100.0

    # Ensure all regions are ordered
    preferred_order = ["eu-north-1", "us-west-2", "sa-east-1", "us-east-1", "ap-south-1"]
    cols = [c for c in preferred_order if c in crosstab.columns] + [c for c in crosstab.columns if c not in preferred_order]
    crosstab = crosstab[cols]

    region_colors = {
        "eu-north-1": "#10B981", # Green (Hydro/Nuclear)
        "us-west-2": "#34D399",  # Mint (Wind/Hydro)
        "sa-east-1": "#FBBF24",  # Yellow (Hydro mix)
        "us-east-1": "#F97316",  # Orange (Gas/Mix)
        "ap-south-1": "#EF4444", # Red (Coal)
    }
    bar_colors = [region_colors.get(c, "#6B7280") for c in cols]

    crosstab.plot(kind="bar", stacked=True, color=bar_colors, ax=ax, edgecolor="#374151", linewidth=0.8, width=0.6)

    ax.set_ylabel("Traffic Share (%)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Routing Policy", fontsize=11, fontweight="bold")
    ax.set_title("Workload Distribution Across Global Cloud Regions\n(Demonstrating Grid Decarbonization)", fontsize=13, fontweight="bold", pad=15)
    ax.set_ylim(0, 105)
    ax.legend(title="Cloud Region (Grid Type)", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.xticks(rotation=0)

    plt.tight_layout()
    output_path = FIGURES_DIR / "regional_traffic_distribution.png"
    plt.savefig(output_path)
    plt.close()
    print(f"Generated: {output_path}")


def main():
    summary_csv = PROJECT_ROOT / "reports" / "benchmark_summary.csv"
    raw_csv = PROJECT_ROOT / "reports" / "benchmark_raw_results.csv"

    if not summary_csv.exists() or not raw_csv.exists():
        print("Benchmark output CSVs not found. Running benchmarks first...")
        from benchmarks.run_comparison import run_benchmark
        run_benchmark(num_requests=1000, sla_ms=250.0, seed=42)

    summary_df = pd.read_csv(summary_csv)
    raw_df = pd.read_csv(raw_csv)

    print("\nGenerating publication figures for FYP Thesis...")
    plot_carbon_comparison(summary_df)
    plot_latency_cdf(raw_df, sla_ms=250.0)
    plot_pareto_tradeoff(summary_df)
    plot_regional_traffic(raw_df)
    print("\nAll 4 thesis figures generated successfully in reports/figures/!")


if __name__ == "__main__":
    main()

