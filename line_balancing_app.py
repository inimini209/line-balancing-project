import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dynamic Line Balancing & Operator Rating", layout="wide")
st.title("🧵 Dynamic Line Balancing & Operator Efficiency Rating App")

# Sidebar file uploads
st.sidebar.header("📥 Upload Files")
skill_file = st.sidebar.file_uploader("Skill Matrix (.xlsx)", type="xlsx")
ob_file    = st.sidebar.file_uploader("Operation Bulletin (.xlsx)", type="xlsx")

if skill_file and ob_file:
    # 1) Read Excel files
    skill_df = pd.read_excel(skill_file)
    ob_df    = pd.read_excel(ob_file)

    # 2) Clean and normalize column names
    skill_df.columns = skill_df.columns.str.strip().str.upper()
    ob_df.columns    = ob_df.columns.str.strip().str.upper()

    # Preview data
    st.subheader("Skill Matrix Preview")
    st.dataframe(skill_df.head(), use_container_width=True)
    st.subheader("Operation Bulletin Preview")
    st.dataframe(ob_df.head(), use_container_width=True)

    # 3) Extract line target (same for all operations)
    if "TARGET" not in ob_df.columns:
        st.error("Operation Bulletin must have a 'TARGET' column.")
    else:
        line_target = ob_df["TARGET"].iloc[0]

        # 4) Allocate operators by highest efficiency for each operation
        assignments = []
        for _, op in ob_df.iterrows():
            op_name = op["OPERATION DESCRIPTION"]
            if op_name in skill_df.columns:
                candidates = skill_df[["OPERATOR NAME", op_name]].dropna()
                if not candidates.empty:
                    best = candidates.loc[candidates[op_name].idxmax()]
                    operator = best["OPERATOR NAME"]
                    efficiency = best[op_name]
                else:
                    operator = "NO SKILLED OP"
                    efficiency = 0
            else:
                operator = "COLUMN NOT FOUND"
                efficiency = 0

            actual_output = (efficiency / 100) * line_target
            assignments.append({
                "OPERATION":       op_name,
                "MACHINE TYPE":    op.get("MACHINE TYPE", ""),
                "ASSIGNED OPERATOR": operator,
                "EFFICIENCY (%)":  efficiency,
                "TARGET":          line_target,
                "ACTUAL OUTPUT":   actual_output
            })

        result_df = pd.DataFrame(assignments)

        # 5) Rate operators by efficiency
        def rate(eff):
            if eff < 65:   return 1
            if eff < 75:   return 2
            if eff < 85:   return 3
            if eff < 95:   return 4
            return 5

        result_df["RATING"] = result_df["EFFICIENCY (%)"].apply(rate)

        # 6) Display results in tabs
        tabs = st.tabs(["📊 Allocation & Output", "⚙️ Operator Ratings", "🛠️ Machine Summary"])

        with tabs[0]:
            st.header("📊 Operation → Operator → Output")
            st.dataframe(result_df[["OPERATION", "MACHINE TYPE", "ASSIGNED OPERATOR", 
                                     "EFFICIENCY (%)", "TARGET", "ACTUAL OUTPUT"]], use_container_width=True)
            st.download_button(
                "📥 Download Allocation Results",
                data=result_df.to_csv(index=False),
                file_name="allocation_results.csv",
                mime="text/csv"
            )

        with tabs[1]:
            st.header("⚙️ Operator-wise Efficiency & Rating")
            op_summary = result_df.groupby("ASSIGNED OPERATOR").agg({
                "TARGET":       "sum",
                "ACTUAL OUTPUT": "sum",
                "EFFICIENCY (%)": "mean"
            }).reset_index()
            op_summary["RATING"] = op_summary["EFFICIENCY (%)"].apply(rate)
            st.dataframe(op_summary.rename(columns={
                "ASSIGNED OPERATOR": "OPERATOR",
                "TARGET": "TOTAL TARGET",
                "ACTUAL OUTPUT": "TOTAL ACTUAL",
                "EFFICIENCY (%)": "AVG EFFICIENCY (%)"
            }), use_container_width=True)
            st.download_button(
                "📥 Download Operator Ratings",
                data=op_summary.to_csv(index=False),
                file_name="operator_ratings.csv",
                mime="text/csv"
            )

        with tabs[2]:
            st.header("🛠️ Machine Type Summary")
            machine_summary = ob_df["MACHINE TYPE"].value_counts().reset_index()
            machine_summary.columns = ["MACHINE TYPE", "OPERATIONS COUNT"]
            st.dataframe(machine_summary, use_container_width=True)
            st.download_button(
                "📥 Download Machine Summary",
                data=machine_summary.to_csv(index=False),
                file_name="machine_summary.csv",
                mime="text/csv"
            )

else:
    st.info("👈 Please upload both the Skill Matrix and Operation Bulletin to proceed.")
