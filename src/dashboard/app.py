"""EcoSyn Interactive Streamlit Web Dashboard.

Department of Information Technology, The University of Haripur
Authors: Riffatullah & Muhammad Saad
Final Year Project: EcoSyn Carbon-Aware Smart Routing Framework
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from config import load_config
from src.carbon_tracker import create_carbon_tracker
from src.router import (
    InvocationRequest,
    LatencyFirstRouter,
    RoundRobinRouter,
    EcoSynRouter,
)
from src.simulator import CloudEnvironment
from src.metrics import MetricsAggregator
from src.storage import DatabaseManager

# Page Configuration
st.set_page_config(
    page_title="EcoSyn Dashboard | Carbon-Aware Cloud Routing",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for university styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1A4D2E;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4F6F52;
        font-weight: 600;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #F8FAF9;
        border-left: 5px solid #1A4D2E;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_system_components():
    config = load_config()
    tracker = create_carbon_tracker(config)
    db_mgr = DatabaseManager(config)
    return config, tracker, db_mgr

config, tracker, db_mgr = get_system_components()

# --- SIDEBAR CONTROLS ---
st.sidebar.image("https://img.icons8.com/color/96/serverless.png", width=70)
st.sidebar.title("🌿 EcoSyn Control Panel")
st.sidebar.markdown("**Final Year Project (BS IT)**\n*The University of Haripur*")
st.sidebar.markdown("---")

st.sidebar.subheader("⚙️ Multi-Objective Weights")
w_carbon = st.sidebar.slider("Carbon Priority Weight (w_c)", 0.0, 1.0, 0.50, 0.05)
w_latency = st.sidebar.slider("Latency Priority Weight (w_l)", 0.0, 1.0, 0.35, 0.05)
w_cost = st.sidebar.slider("Cost Priority Weight (w_p)", 0.0, 1.0, 0.15, 0.05)

# Auto-normalize weights in UI
total_w = w_carbon + w_latency + w_cost
if total_w > 0:
    w_c_norm = w_carbon / total_w
    w_l_norm = w_latency / total_w
    w_p_norm = w_cost / total_w
else:
    w_c_norm, w_l_norm, w_p_norm = 0.5, 0.35, 0.15

st.sidebar.caption(f"Normalized: Carbon: **{w_c_norm:.2f}** | Latency: **{w_l_norm:.2f}** | Cost: **{w_p_norm:.2f}**")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Service Level Agreement (SLA)")
sla_threshold = st.sidebar.slider("Max Acceptable Latency SLA (ms)", 100.0, 500.0, 250.0, 10.0)

st.sidebar.markdown("---")
st.sidebar.info("Developed by:\n**Muhammad Saad & Riffatullah**\nSupervised by: Dept of IT")

# --- HEADER SECTION ---
st.markdown('<div class="main-title">🌿 EcoSyn: Carbon-Aware Smart Routing Framework</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Intelligent Request Routing for Sustainable Serverless Cloud Computing | University of Haripur</div>', unsafe_allow_html=True)

# Tabs
tab_map, tab_dispatch, tab_benchmark, tab_logs = st.tabs([
    "🌍 Global Cloud Carbon Map",
    "⚡ Live Dispatch & Decision Explainer",
    "📊 Comparative Benchmark Suite",
    "🗄️ Invocation Telemetry Database",
])

# ==============================================================================
# TAB 1: GLOBAL CARBON MAP & REGION STATUS
# ==============================================================================
with tab_map:
    st.subheader("Global Cloud Data Center Regions & Grid Carbon Intensities")
    st.markdown("Real-time emission rates per region ($gCO_2eq / kWh$) powering serverless function containers.")

    regions_data = []
    current_carbons = tracker.get_all_regions_carbon(timestamp_sec=0.0)
    regions_cfg = config.get("regions", {})

    for r_id, r_info in regions_cfg.items():
        carb = current_carbons.get(r_id, r_info.get("base_carbon_intensity", 300.0))
        regions_data.append({
            "Region ID": r_id,
            "Name": r_info.get("name"),
            "Country": r_info.get("country"),
            "Latitude": r_info.get("latitude"),
            "Longitude": r_info.get("longitude"),
            "Carbon Intensity (gCO2/kWh)": carb,
            "PUE": r_info.get("pue"),
            "Power (W)": r_info.get("hardware_active_power_watts"),
        })

    reg_df = pd.DataFrame(regions_data)

    # Plotly Geographic Map
    fig_map = px.scatter_geo(
        reg_df,
        lat="Latitude",
        lon="Longitude",
        hover_name="Name",
        hover_data=["Region ID", "Carbon Intensity (gCO2/kWh)", "PUE"],
        size=[35] * len(reg_df),
        color="Carbon Intensity (gCO2/kWh)",
        color_continuous_scale=["#10B981", "#FBBF24", "#F97316", "#EF4444"],
        projection="natural earth",
        title="Simulated Global Serverless Cloud Infrastructure",
    )
    fig_map.update_layout(height=480, margin={"r": 0, "t": 35, "l": 0, "b": 0})
    st.plotly_chart(fig_map, use_container_width=True)

    # Metric Cards across columns
    st.markdown("### Regional Grid Profiles")
    cols = st.columns(len(regions_data))
    for idx, reg in enumerate(regions_data):
        with cols[idx]:
            carb_val = reg["Carbon Intensity (gCO2/kWh)"]
            status_color = "🟢" if carb_val < 150 else ("🟡" if carb_val < 400 else "🔴")
            st.metric(
                label=f"{status_color} {reg['Region ID']}",
                value=f"{carb_val:.1f} gCO2",
                delta=f"PUE: {reg['PUE']}",
                delta_color="off",
            )
            st.caption(f"**{reg['Name']}**")

# ==============================================================================
# TAB 2: LIVE DISPATCH & DECISION EXPLAINER
# ==============================================================================
with tab_dispatch:
    st.subheader("Interactive Request Dispatcher & Decision Explainer")
    st.markdown("Dispatch a single serverless invocation to see how **EcoSyn** routes the request compared to standard cloud baselines.")

    c1, c2, c3 = st.columns(3)
    with c1:
        client_origin = st.selectbox(
            "Client Geographic Origin",
            ["client-north-america", "client-europe", "client-asia", "client-south-america"],
            index=0,
        )
    with c2:
        function_type = st.selectbox(
            "Serverless Function Type",
            [
                ("image-resizer", 512, 140.0),
                ("data-aggregator", 1024, 220.0),
                ("auth-service", 128, 40.0),
                ("payment-process", 512, 110.0),
            ],
            format_func=lambda x: f"{x[0]} ({x[1]} MB, ~{x[2]} ms)",
        )
    with c3:
        req_sla = st.number_input("Request SLA Deadline (ms)", value=float(sla_threshold), step=10.0)

    if st.button("🚀 Route & Dispatch Request", type="primary"):
        fn_name, fn_mem, fn_dur = function_type
        req = InvocationRequest(
            request_id="interactive-demo",
            timestamp_sec=0.0,
            client_region=client_origin,
            function_name=fn_name,
            memory_mb=fn_mem,
            estimated_duration_ms=fn_dur,
            sla_deadline_ms=req_sla,
        )

        # Routers
        r_lat = LatencyFirstRouter(config, tracker)
        r_rr = RoundRobinRouter(config, tracker)
        r_eco = EcoSynRouter(config, tracker, carbon_weight=w_c_norm, latency_weight=w_l_norm, cost_weight=w_p_norm)

        env = CloudEnvironment(config, tracker)
        res_lat = env.dispatch(req, r_lat.route(req))
        res_rr = env.dispatch(req, r_rr.route(req))
        res_eco = env.dispatch(req, r_eco.route(req))

        st.markdown("---")
        st.markdown("### Head-to-Head Dispatch Outcome")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown("#### 🔵 Latency-First (Standard)")
            st.write(f"**Target Region:** `{res_lat.selected_region}`")
            st.write(f"**Response Time:** `{res_lat.total_latency_ms:.1f} ms`")
            st.write(f"**Carbon Emitted:** `{res_lat.carbon_emissions_g:.6f} g`")
            st.write(f"**SLA Compliance:** {'✅ Satisfied' if not res_lat.sla_violated else '❌ Breached'}")

        with col_b:
            st.markdown("#### 🟡 Round-Robin (Baseline)")
            st.write(f"**Target Region:** `{res_rr.selected_region}`")
            st.write(f"**Response Time:** `{res_rr.total_latency_ms:.1f} ms`")
            st.write(f"**Carbon Emitted:** `{res_rr.carbon_emissions_g:.6f} g`")
            st.write(f"**SLA Compliance:** {'✅ Satisfied' if not res_rr.sla_violated else '❌ Breached'}")

        with col_c:
            st.markdown("#### 🌿 EcoSyn (Proposed)")
            st.write(f"**Target Region:** `{res_eco.selected_region}`")
            st.write(f"**Response Time:** `{res_eco.total_latency_ms:.1f} ms`")
            st.write(f"**Carbon Emitted:** `{res_eco.carbon_emissions_g:.6f} g`")
            st.write(f"**SLA Compliance:** {'✅ Satisfied' if not res_eco.sla_violated else '❌ Breached'}")

        # Savings badge
        if res_lat.carbon_emissions_g > 0:
            saved_pct = ((res_lat.carbon_emissions_g - res_eco.carbon_emissions_g) / res_lat.carbon_emissions_g) * 100.0
            st.success(f"🌱 **EcoSyn achieved {saved_pct:.1f}% carbon reduction** compared to standard Latency-First routing while keeping execution within the SLA constraint!")

        st.info(f"**Decision Explainer:** {res_eco.decision_notes}")

# ==============================================================================
# TAB 3: COMPARATIVE BENCHMARK SUITE
# ==============================================================================
with tab_benchmark:
    st.subheader("Automated Head-to-Head Comparative Benchmark")
    st.markdown("Execute a batch simulation of 100 to 1,000 serverless requests across all routing policies.")

    b_col1, b_col2 = st.columns([1, 2])
    with b_col1:
        num_reqs = st.select_slider("Batch Workload Volume", options=[100, 250, 500, 1000], value=500)
        run_bench_btn = st.button("▶ Run Full Benchmark", type="primary")

    if run_bench_btn:
        with st.spinner(f"Simulating {num_reqs} requests across 4 routing algorithms..."):
            from benchmarks.run_comparison import run_benchmark
            result_data = run_benchmark(num_requests=num_reqs, sla_ms=sla_threshold, seed=42, persist_to_db=True)
            summaries = result_data["summaries"]
            sum_df = pd.DataFrame(summaries)

            st.success(f"Benchmark completed successfully for {num_reqs} requests!")

            # Metric Cards
            m1, m2, m3, m4 = st.columns(4)
            lat_first = sum_df[sum_df["policy_label"] == "Latency-First"].iloc[0]
            eco_bal = sum_df[sum_df["policy_label"] == "EcoSyn-Balanced"].iloc[0]
            eco_grn = sum_df[sum_df["policy_label"] == "EcoSyn-Green"].iloc[0]

            m1.metric("Latency-First Carbon", f"{lat_first['total_carbon_g']:.4f} g")
            m2.metric("EcoSyn-Balanced Carbon", f"{eco_bal['total_carbon_g']:.4f} g", f"-{eco_bal['carbon_saved_pct']:.1f}%")
            m3.metric("EcoSyn-Green Carbon", f"{eco_grn['total_carbon_g']:.4f} g", f"-{eco_grn['carbon_saved_pct']:.1f}%")
            m4.metric("EcoSyn Avg Latency", f"{eco_bal['avg_latency_ms']:.1f} ms", f"SLA: {sla_threshold} ms")

            # Plotly Charts
            st.markdown("### Benchmark Visualizations")
            ch_col1, ch_col2 = st.columns(2)

            with ch_col1:
                fig_bar = px.bar(
                    sum_df,
                    x="policy_label",
                    y="total_carbon_g",
                    color="policy_label",
                    color_discrete_map={
                        "Latency-First": "#3B82F6",
                        "Round-Robin": "#F59E0B",
                        "EcoSyn-Balanced": "#10B981",
                        "EcoSyn-Green": "#047857",
                    },
                    title="Total Carbon Emissions by Policy (gCO2eq)",
                    labels={"total_carbon_g": "Emissions (gCO2eq)", "policy_label": "Policy"},
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            with ch_col2:
                fig_lat = px.bar(
                    sum_df,
                    x="policy_label",
                    y="avg_latency_ms",
                    color="policy_label",
                    color_discrete_map={
                        "Latency-First": "#3B82F6",
                        "Round-Robin": "#F59E0B",
                        "EcoSyn-Balanced": "#10B981",
                        "EcoSyn-Green": "#047857",
                    },
                    title="Average Response Time by Policy (ms)",
                    labels={"avg_latency_ms": "Average Latency (ms)", "policy_label": "Policy"},
                )
                st.plotly_chart(fig_lat, use_container_width=True)

# ==============================================================================
# TAB 4: INVOCATION TELEMETRY DATABASE
# ==============================================================================
with tab_logs:
    st.subheader("Persisted Invocation Telemetry (SQLite / MySQL)")
    st.markdown("Live database records stored by `DatabaseManager` during execution.")

    policy_filter = st.selectbox("Filter by Policy", ["All", "ecosyn", "latency_first", "round_robin"])
    filter_val = None if policy_filter == "All" else policy_filter

    logs = db_mgr.get_invocation_logs(policy=filter_val, limit=200)

    if logs:
        log_df = pd.DataFrame(logs)
        st.dataframe(log_df, use_container_width=True)

        csv = log_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Export Telemetry as CSV", data=csv, file_name="ecosyn_telemetry.csv", mime="text/csv")
    else:
        st.info("No telemetry logs found in database. Run a benchmark or dispatch an invocation to populate logs!")

st.markdown("---")
st.caption("Department of Information Technology, The University of Haripur • FYP Final Submission")

