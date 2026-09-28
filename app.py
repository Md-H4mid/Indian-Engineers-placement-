import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from Database import run_query

st.set_page_config(page_title="Indian Engineering Placement Dashboard", page_icon="🎓", layout="wide")

# Inject deep modern dark-mode aesthetic styling
st.markdown("""
    <style>
        .block-container {padding-top: 2rem; padding-bottom: 2rem;}
        h1, h2, h3 {color: #00FFCC !important; font-weight: 700;}
        .stMetric {background-color: #1E1E2F; padding: 15px; border-radius: 10px; border: 1px solid #33334D;}
        div[data-testid="stMetricValue"] {color: #00FFCC;}
    </style>
""", unsafe_allow_html=True)

def get_column_values(column_name):
    query = f"SELECT DISTINCT {column_name} FROM students WHERE {column_name} IS NOT NULL ORDER BY {column_name};"
    return run_query(query)[column_name].tolist()

st.title("🎓 Indian Engineering Placement Analytics")
st.caption("Explore placement drivers, institutional differences, skill benchmarks and scenario-based projections.")

st.sidebar.header("🔣 Cohort Filters")
tier_options = get_column_values("College_Tier")
branch_options = get_column_values("Branch")

selected_tiers = st.sidebar.multiselect("College Tier", options=tier_options, default=tier_options)
selected_branches = st.sidebar.multiselect("Branch", options=branch_options, default=branch_options)
cgpa_range = st.sidebar.slider("CGPA Range", min_value=5.0, max_value=10.0, value=(5.0, 10.0), step=0.1)
min_dsa = st.sidebar.slider("Minimum DSA Problems Solved", min_value=0, max_value=1200, value=0, step=50)

if not selected_tiers or not selected_branches:
    st.warning("Please select at least one College Tier and one Branch.")
    st.stop()

tier_parameters = {f"tier_{i}": t for i, t in enumerate(selected_tiers)}
branch_parameters = {f"branch_{i}": b for i, b in enumerate(selected_branches)}
tier_placeholders = [f":{k}" for k in tier_parameters.keys()]
branch_placeholders = [f":{k}" for k in branch_parameters.keys()]

where_clause = f"""
    WHERE College_Tier IN ({", ".join(tier_placeholders)})
    AND Branch IN ({", ".join(branch_placeholders)})
    AND CGPA BETWEEN :cgpa_min AND :cgpa_max
    AND DSA_Problems_Solved >= :min_dsa
"""

query_parameters = {**tier_parameters, **branch_parameters, "cgpa_min": float(cgpa_range[0]), "cgpa_max": float(cgpa_range[1]), "min_dsa": int(min_dsa)}
cohort_data = run_query(f"SELECT * FROM students {where_clause};", query_parameters)

if cohort_data.empty:
    st.warning("No students match the selected filters.")
    st.stop()

placed_cohort = cohort_data[cohort_data["Placement_Status"] == "Placed"].copy()
total_count = len(cohort_data)
placed_count = len(placed_cohort)
placement_rate = (placed_count / total_count * 100) if total_count > 0 else 0
avg_lpa, peak_lpa = (placed_cohort["Package_LPA"].mean(), placed_cohort["Package_LPA"].max()) if not placed_cohort.empty else (0, 0)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Students", f"{total_count:,}")
col2.metric("Placed Students", f"{placed_count:,}")
col3.metric("Placement Rate", f"{placement_rate:.2f}%")
col4.metric("Average Package", f"₹{avg_lpa:.2f} LPA")
st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Core Drivers", "🏫 Institutional & Branches", "🧠 Skill Benchmarks", "🔮 Future Scenarios", "💻 SQL Sandbox"])

with tab1:
    st.header("Core Placement Drivers")
    st.subheader("DSA Problems vs Package")
    scatter_columns = ["DSA_Problems_Solved", "Package_LPA", "College_Tier", "GitHub_Contributions", "Student_ID", "Branch", "CGPA", "Internships_Count", "Competitive_Programming_Rating"]
    avail_cols = [c for c in scatter_columns if c in placed_cohort.columns]
    scatter_data = placed_cohort[avail_cols].copy()
    
    if not scatter_data.empty:
        fig_scatter = px.scatter(scatter_data, x="DSA_Problems_Solved", y="Package_LPA", color="College_Tier", 
                                 size="GitHub_Contributions" if "GitHub_Contributions" in scatter_data.columns else None, 
                                 size_max=18, opacity=0.8, color_discrete_sequence=px.colors.qualitative.Prism, template="plotly_dark",
                                 labels={"DSA_Problems_Solved": "DSA Problems Solved", "Package_LPA": "Package (LPA)", "College_Tier": "College Tier"},
                                 hover_data=[c for c in ["Student_ID", "Branch", "CGPA", "GitHub_Contributions", "Internships_Count", "Competitive_Programming_Rating"] if c in scatter_data.columns])
        fig_scatter.update_layout(height=450, xaxis_title="DSA Problems Solved", yaxis_title="Package (LPA)")
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.subheader("Projects vs Internships — Placement Rate")
    if "Projects_Count" in cohort_data.columns and "Internships_Count" in cohort_data.columns:
        heatmap_data = cohort_data.groupby(["Projects_Count", "Internships_Count"])["Placement_Status"].apply(lambda x: (x == "Placed").mean() * 100).reset_index(name="Placement_Rate")
        fig_heatmap = px.imshow(heatmap_data.pivot(index="Projects_Count", columns="Internships_Count", values="Placement_Rate"), 
                                text_auto=".1f", aspect="auto", template="plotly_dark", color_continuous_scale="Viridis",
                                labels={"x": "Internships Count", "y": "Projects Count", "color": "Placement Rate (%)"})
        fig_heatmap.update_layout(height=450)
        st.plotly_chart(fig_heatmap, use_container_width=True)

with tab2:
    st.header("Institutional & Branch Analysis")
    st.subheader("Branch-wise Placement Performance")
    b_summary = cohort_data.groupby("Branch").agg(Total_Students=("Student_ID", "count"), Placement_Rate=("Placement_Status", lambda x: (x == "Placed").mean() * 100)).reset_index()
    p_b_data = placed_cohort.groupby("Branch")["Package_LPA"].mean().reset_index(name="Average_Package_LPA")
    b_summary = b_summary.merge(p_b_data, on="Branch", how="left")
    
    fig_branch = px.bar(b_summary, x="Branch", y="Placement_Rate", color="Average_Package_LPA", text="Placement_Rate", template="plotly_dark", color_continuous_scale="IceFire",
                        labels={"Placement_Rate": "Placement Rate (%)", "Average_Package_LPA": "Average Package (LPA)"})
    fig_branch.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig_branch.update_layout(height=450)
    st.plotly_chart(fig_branch, use_container_width=True)

    st.subheader("Package Distribution by College Tier")
    if not placed_cohort.empty:
        fig_box = px.box(placed_cohort, x="College_Tier", y="Package_LPA", points="outliers", template="plotly_dark", color="College_Tier", color_discrete_sequence=px.colors.qualitative.Pastel,
                         labels={"College_Tier": "College Tier", "Package_LPA": "Package (LPA)"})
        fig_box.update_layout(height=450)
        st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("College Tier → Branch → Placement Status")
    sunburst_data = cohort_data.copy()
    sunburst_data["Student_Count"] = 1
    fig_sunburst = px.sunburst(sunburst_data, path=["College_Tier", "Branch", "Placement_Status"], values="Student_Count", color="Package_LPA", template="plotly_dark", color_continuous_scale="RdBu",
                               labels={"Student_Count": "Students", "Package_LPA": "Package (LPA)"})
    fig_sunburst.update_layout(height=550)
    st.plotly_chart(fig_sunburst, use_container_width=True)

with tab3:
    st.header("Skill Benchmark Analysis")
    radar_metrics = ["CGPA", "DSA_Problems_Solved", "Aptitude_Score", "Communication_Score", "Soft_Skills_Score"]
    avail_radar = [c for c in radar_metrics if c in cohort_data.columns]
    
    if len(avail_radar) >= 3:
        r_data = cohort_data[avail_radar + ["Package_LPA"]].copy()
        scaled_df = pd.DataFrame()
        for col in avail_radar:
            mn, mx = r_data[col].min(), r_data[col].max()
            scaled_df[col] = 0 if mx == mn else ((r_data[col] - mn) / (mx - mn) * 100)
        scaled_df["Package_LPA"] = r_data["Package_LPA"]
        
        c_means = scaled_df[avail_radar].mean().tolist()
        hp_group = scaled_df[scaled_df["Package_LPA"] >= 20]
        hp_means = hp_group[avail_radar].mean().tolist() if not hp_group.empty else [0]*len(avail_radar)
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=c_means, theta=avail_radar, fill="toself", name="Cohort Average", fillcolor="rgba(0, 255, 204, 0.2)", line=dict(color="#00FFCC")))
        fig_radar.add_trace(go.Scatterpolar(r=hp_means, theta=avail_radar, fill="toself", name="20+ LPA Group", fillcolor="rgba(255, 0, 128, 0.2)", line=dict(color="#FF0080")))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), title="20+ LPA Group vs Cohort Average", template="plotly_dark", height=500)
        st.plotly_chart(fig_radar, use_container_width=True)

    st.subheader("Package Distribution by Branch and Gender")
    if not placed_cohort.empty and "Gender" in placed_cohort.columns:
        fig_violin = px.violin(placed_cohort, x="Branch", y="Package_LPA", color="Gender", box=True, points="outliers", template="plotly_dark", color_discrete_sequence=["#00FFCC", "#FF0080"], labels={"Package_LPA": "Package (LPA)"})
        fig_violin.update_layout(height=500)
        st.plotly_chart(fig_violin, use_container_width=True)

    st.subheader("Package Distribution by College Tier")
    if not placed_cohort.empty:
        fig_hist = px.histogram(placed_cohort, x="Package_LPA", color="College_Tier", nbins=30, template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Safe, labels={"Package_LPA": "Package (LPA)"})
        fig_hist.update_layout(height=450)
        st.plotly_chart(fig_hist, use_container_width=True)

with tab4:
    st.header("🔮 Future Scenario Analysis")
    st.info("The projection below is a scenario model based on a 35% assumption. It is not a guaranteed future salary prediction.")
    
    if not placed_cohort.empty:
        proj_df = placed_cohort[["DSA_Problems_Solved", "Package_LPA"]].copy()
        bins = [-1] + list(range(100, 1201, 100))
        labels = [f"{s+1}-{e}" for s, e in zip(bins[:-1], bins[1:])]
        proj_df["DSA_Band"] = pd.cut(proj_df["DSA_Problems_Solved"], bins=bins, labels=labels, include_lowest=True)
        
        d_summary = proj_df.groupby("DSA_Band", observed=False).agg(Average_Package_LPA=("Package_LPA", "mean"), Average_DSA=("DSA_Problems_Solved", "mean")).reset_index().dropna(subset=["Average_Package_LPA"])
        d_summary["Scenario_Package_LPA"] = d_summary["Average_Package_LPA"] * (1 + (d_summary["Average_DSA"] / 1000) * 0.35)
        
        fig_proj = go.Figure()
        fig_proj.add_trace(go.Scatter(x=d_summary["DSA_Band"], y=d_summary["Average_Package_LPA"], mode="lines+markers", name="Current Avg Package", line=dict(color="#00FFCC")))
        fig_proj.add_trace(go.Scatter(x=d_summary["DSA_Band"], y=d_summary["Scenario_Package_LPA"], mode="lines+markers", name="Scenario Package", line=dict(color="#FF0080")))
        fig_proj.update_layout(title="DSA vs Package — Scenario-Based Projection", xaxis_title="DSA Problems Band", yaxis_title="Package (LPA)", template="plotly_dark", height=500)
        st.plotly_chart(fig_proj, use_container_width=True)
        st.dataframe(d_summary, use_container_width=True)

    st.subheader("Candidate Criteria Funnel")
    cg_c = cohort_data[cohort_data["CGPA"] >= 7]
    int_c = cg_c[cg_c["Internships_Count"] >= 1]
    dsa_c = int_c[int_c["DSA_Problems_Solved"] >= 150]
    p_c = dsa_c[dsa_c["Placement_Status"] == "Placed"]
    
    f_data = pd.DataFrame({"Stage": ["Total Students", "CGPA >= 7", "Internship >= 1", "DSA >= 150", "Placed"], "Students": [total_count, len(cg_c), len(int_c), len(dsa_c), len(p_c)]})
    fig_funnel = px.funnel(f_data, y="Stage", x="Students", template="plotly_dark", color_discrete_sequence=["#FF0080"])
    fig_funnel.update_layout(title="Candidate Qualification Funnel", height=500)
    st.plotly_chart(fig_funnel, use_container_width=True)

with tab5:
    st.header("💻 SQL Sandbox")
    st.write("Run SELECT queries against the `students` table.")
    default_sql = "SELECT\n    College_Tier,\n    COUNT(*) AS Total_Students,\n    AVG(DSA_Problems_Solved) AS Average_DSA,\n    AVG(CASE WHEN Placement_Status = 'Placed' THEN 1.0 ELSE 0.0 END) * 100 AS Placement_Rate,\n    AVG(CASE WHEN Placement_Status = 'Placed' THEN Package_LPA END) AS Average_Placed_Package\nFROM students\nGROUP BY College_Tier\nORDER BY College_Tier;"
    
    sql_query = st.text_area("Enter SQL Query", value=default_sql, height=200)
    if st.button("▶ Run SQL"):
        cleaned = sql_query.strip().upper()
        if not cleaned.startswith("SELECT"):
            st.error("Only SELECT queries are allowed.")
        elif ";" in cleaned[:-1]:
            st.error("Multiple SQL statements are not allowed.")
        else:
            try:
                res = run_query(sql_query)
                st.success(f"Query executed successfully — {len(res)} rows returned.")
                st.dataframe(res, use_container_width=True)
            except Exception as e:
                st.error(f"SQL Error: {e}")

st.divider()
st.caption("Indian Engineering Placement Analytics | Python + Pandas + MySQL + Streamlit + Plotly")
