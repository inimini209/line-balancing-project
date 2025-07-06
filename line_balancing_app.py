import streamlit as st
import pandas as pd
from difflib import get_close_matches

st.set_page_config(page_title="Line Balancing & Operator Rating", layout="wide")
st.title("🧵 Dynamic Line Balancing & Operator Efficiency Rating App (with Fuzzy Mapping)")

def combine_similar_operations(ob_df, sam_threshold=1.0, keywords=("IRON", "PRESS")):
    ob_df = ob_df.copy()
    used_idx = set()
    combined_rows = []
    combine_map = dict()  # Map combined operation name to list of originals
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
            combine_map[combined_op_name] = matches["OPERATION DESCRIPTION"].tolist()
    not_combined = ob_df[~ob_df.index.isin(used_idx)]
    combined_df = pd.DataFrame(combined_rows)
    new_ob_df = pd.concat([not_combined, combined_df], ignore_index=True)
    return new_ob_df, combine_map

def clean_string(s):
    if pd.isnull(s): return ""
    return (str(s)
            .replace('\n', ' ')
            .replace('\r', ' ')
            .replace('\t', ' ')
            .replace('  ', ' ')
            .strip()
            .upper())

st.sidebar.header("📥 Upload Your Files")
skill_file = st.sidebar.file_uploader("Skill Matrix (.xlsx)", type="xlsx")
ob_file    = st.sidebar.file_uploader("Operation Bulletin (.xlsx)", type="xlsx")

if skill_file and ob_file:
    skill_df = pd.read_excel(skill_file)
    ob_df = pd.read_excel(ob_file)

    # Clean columns
    skill_df.columns = [clean_string(col) for col in skill_df.columns]
    ob_df.columns = [clean_string(col) for col in ob_df.columns]
    ob_df["OPERATION DESCRIPTION"] = ob_df["OPERATION DESCRIPTION"].apply(clean_string)

    st.subheader("Skill Matrix Columns (cleaned)")
    st.write(skill_df.columns.tolist())
    st.subheader("OB Operation Descriptions (cleaned)")
    st.write(ob_df["OPERATION DESCRIPTION"].unique().tolist())

    required_ob = {"OPERATION DESCRIPTION", "MACHINE TYPE", "TARGET", "MACHINE SAM", "MANUAL SAM"}
    if not required_ob.issubset(ob_df.columns):
        st.error(f"OB file must contain columns: {required_ob}")
        st.stop()
    if "OPERATOR NAME" not in skill_df.columns:
        st.error("Skill Matrix must contain column: OPERATOR NAME")
        st.stop()

    # --- Build OPERATION_MAP using fuzzy matching (for operations not matching Skill Matrix columns) ---
    skill_cols = [col for col in skill_df.columns if col != "OPERATOR NAME"]
    ob_ops = ob_df["OPERATION DESCRIPTION"].unique()
    OPERATION_MAP = {}
    for op in ob_ops:
        if op not in skill_cols:
            suggestions = get_close_matches(op, skill_cols, n=1, cutoff=0.6)
            if suggestions:
                OPERATION_MAP[op] = suggestions[0]
    if OPERATION_MAP:
        st.info("Auto-generated OPERATION_MAP (fuzzy-matched):")
        st.code(f"OPERATION_MAP = {OPERATION_MAP}", language="python")

    # --- Combine similar/low-SAM operations
    ob_df, combine_map = combine_similar_operations(
        ob_df, sam_threshold=1.0, keywords=("IRON", "PRESS")
    )

    st.subheader("Operation Bulletin Preview (after combining)")
    st.dataframe(ob_df.head(), use_container_width=True)

    line_target = ob_df["TARGET"].iloc[0]
    assignments = []
    assigned_operators = set()

    for _, row in ob_df.iterrows():
        ob_op_name = row["OPERATION DESCRIPTION"]

        # Use mapping if available, else the original name
        skill_col = OPERATION_MAP.get(ob_op_name, ob_op_name)
        machine = row["MACHINE TYPE"]

        # If this is a combined operation, look up best operator based on the best efficiency in any combined operation (apply mapping to combined ops)
        if ob_op_name in combine_map:
            combined_cols = [OPERATION_MAP.get(c, c) for c in combine_map[ob_op_name]]
            effs = []
            for _, op_row in skill_df.iterrows():
                eff_list = [op_row[c] for c in combined_cols if c in skill_df.columns and not pd.isna(op_row[c])]
                if eff_list:
                    max_eff = max(eff_list)
                    effs.append((op_row["OPERATOR NAME"], max_eff))
            effs = [t for t in effs if t[0] not in assigned_operators]
            if effs:
                operator, efficiency = max(effs, key=lambda x: x[1])
                assigned_operators.add(operator)
            else:
                operator, efficiency = "NO SKILLED OP", 0
        # Else, assign normally using mapping
        elif skill_col in skill_df.columns:
            candidates = skill_df[["OPERATOR NAME", skill_col]].dropna()
            candidates = candidates[~candidates["OPERATOR NAME"].isin(assigned_operators)]
            if not candidates.empty:
                best       = candidates.loc[candidates[skill_col].idxmax()]
                operator   = best["OPERATOR NAME"]
                efficiency = best[skill_col]
                assigned_operators.add(operator)
            else:
                operator, efficiency = "NO SKILLED OP", 0
        else:
            operator, efficiency = "COLUMN NOT FOUND", 0

        actual_output = (efficiency / 100) * line_target
        assignments.append({
            "OPERATION":         ob_op_name,
            "MACHINE TYPE":      machine,
            "ASSIGNED OPERATOR": operator,
            "EFFICIENCY (%)":    efficiency,
            "TARGET":            line_target,
            "ACTUAL OUTPUT":     actual_output
        })

    result_df = pd.DataFrame(assignments)

    # --- SHOW WARNING IF ANY OPERATOR IS NOT FOUND ---
    missing_ops = result_df[result_df["ASSIGNED OPERATOR"].isin(["NO SKILLED OP", "COLUMN NOT FOUND"])]
    if not missing_ops.empty:
        st.warning(
            "⚠️ **No skilled operator found for the following operations:**\n\n" +
            "\n".join(f"- {row['OPERATION']}" for _, row in missing_ops.iterrows())
        )
    # -------------------------------------------------

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
