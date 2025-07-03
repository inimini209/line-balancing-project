import streamlit as st
import pandas as pd

st.set_page_config(page_title="Line Balancing & Operator Rating", layout="wide")
st.title("🧵 Dynamic Line Balancing & Operator Efficiency Rating App")

def combine_similar_operations(ob_df, sam_threshold=1.0, keywords=("IRON", "PRESS")):
    ob_df = ob_df.copy()
    used_idx = set()
    combined_rows = []
    for keyword in keywords:
        matches = ob_df[
            ob_df["OPERATION DESCRIPTION"].str.upper().str.contains(keyword)
            & ((ob_df["MACHINE SAM"].fillna(0) + ob_df["MANUAL SAM"].fillna(0)) < sam_threshold)
            & (~ob_df.index.isin(used_idx))
        ]
        if len(matches) > 1:
            indices = matches.index
            used_idx.update(indices)
            combined_op_name = f"COMBINED {keyword} OPERATIONS"
            machine_types = ", ".join(matches["MACHINE TYPE"].astype(str).unique())
            target = matches["TARGET"].iloc[0]
            sam_machine = matches["MACHINE SAM"].sum()
            sam_manual = matches["MANUAL SAM"].sum()
            combined_rows.append({
                "OPERATION DESCRIPTION": combined_op_name,
                "MACHINE SAM": sam_machine,
                "MANUAL SAM": sam_manual,
                "MACHINE TYPE": machine_types,
                "TARGET": target
            })
    not_combined = ob_df[~ob_df.index.isin(used_idx)]
    combined_df = pd.DataFrame(combined_rows)
    new_ob_df = pd.concat([not_combined, combined_df], ignore_index=True)
    return new_ob_df

# Sidebar — file uploads
st.sidebar.header("📥 Upload Your Files")
skill_file = st.sidebar.file_uploader("Skill Matrix (.xlsx)", type="xlsx")
ob_file    = st.sidebar.file_uploader("Operation Bulletin (.xlsx)", type="xlsx")

if skill_file and ob_file:
    skill_df = pd.read_excel(skill_file)
    skill_df.columns = (
        skill_df.columns
        .str.replace('\n', ' ', regex=True)
        .str.strip()
        .str.upper()
    )

    ob_df = pd.read_excel(ob_file)
    ob_df.columns = (
        ob_df.columns
        .str.replace('\n', ' ', regex=True)
        .str.strip()
        .str.upper()
    )

    st.subheader("Skill Matrix Preview")
    st.dataframe(skill_df.head(), use_container_width=True)
    st.subheader("Operation Bulletin Preview (before combining)")
    st.dataframe(ob_df.head(), use_container_width=True)

    required_ob = {"OPERATION DESCRIPTION", "MACHINE TYPE", "TARGET", "MACHINE SAM", "MANUAL SAM"}
    if not required_ob.issubset(ob_df.columns):
        st.error(f"OB file must contain columns: {required_ob}")
        st.stop()
    if "OPERATOR NAME" not in skill_df.columns:
        st.error("Skill Matrix must contain column: OPERATOR NAME")
        st.stop()

    # --- Combine similar/low-SAM operations
    ob_df = combine_similar_operations(ob_df, sam_threshold=1.0, keywords=("IRON", "PRESS"))

    st.subheader("Operation Bulletin Preview (after combining)")
    st.dataframe(ob_df.head(), use_container_width=True)

    line_target = ob_df["TARGET"].iloc[0]
    assignments = []
    assigned_operators = set()

    for _, row in ob_df.iterrows():
        op_name = row["OPERATION DESCRIPTION"]
        machine = row["MACHINE TYPE"]

        if op_name in skill_df.columns:
            candidates = skill_df[["OPERATOR NAME", op_name]].dropna()
            candidates = candidates[~candidates["OPERATOR NAME"].isin(assigned_operators)]
            if not candidates.empty:
                best       = candidates.loc[candidates[op_name].idxmax()]
                operator   = best["OPERATOR NAME"]
                efficiency = best[op_name]
                assigned_operators.add(operator)
            else:
                operator, efficiency = "NO SKILLED OP", 0
        else:
            operator, efficiency = "COLUMN NOT FOUND", 0

        actual_output = (efficiency / 100) * line_target
        assignments.append({
            "OPERATION":         op_name,
            "MACHINE TYPE":      machine,
            "ASSIGNED OPERATOR": operator,
            "EFFICIENCY (%)":    efficiency,
            "TARGET":            line_target,
            "ACTUAL OUTPUT":     actual_output
        })

    result_df = pd.DataFrame(assignments)

    def rate(e):
        if e < 65: return 1
        if e < 75: return 2
        if e < 85: return 3
        if e < 95: return 4
        return 5

    result_df["RATING"] = result_df["EFFICIENCY (%)"].apply(rate)

    tabs = st.tabs(["📊 Allocation & Output", "⚙️ Operator Ratings", "🛠️ Machine Summary"])

    with tabs[0]:
        st.header("📊 Operation → Operator → Output")
        st.dataframe(
            result_df[[
                "OPERATION", "MACHINE TYPE", "ASSIGNED OPERATOR",
                "EFFICIENCY (%)", "TARGET", "ACTUAL OUTPUT"
            ]],
            use_container_width=True
        )

    with tabs[1]:
        st.header("⚙️ Operator-wise Efficiency & Rating")
        op_summary = result_df.groupby("ASSIGNED OPERATOR", dropna=False).agg({
            "TARGET":          "sum",
            "ACTUAL OUTPUT":   "sum",
            "EFFICIENCY (%)":  "mean"
        }).reset_index()
        op_summary["RATING"] = op_summary["EFFICIENCY (%)"].apply(rate)
        st.dataframe(
            op_summary.rename(columns={
                "ASSIGNED OPERATOR": "OPERATOR",
                "TARGET":            "TOTAL TARGET",
                "ACTUAL OUTPUT":     "TOTAL OUTPUT",
                "EFFICIENCY (%)":    "AVG EFFICIENCY (%)"
            }),
            use_container_width=True
        )

    with tabs[2]:
        st.header("🛠️ Machine Type Summary")
        machine_summary = ob_df["MACHINE TYPE"].value_counts().reset_index()
        machine_summary.columns = ["MACHINE TYPE", "OPERATIONS COUNT"]
        st.dataframe(machine_summary, use_container_width=True)

else:
    st.info("👈 Please upload both the Skill Matrix and Operation Bulletin files.")
