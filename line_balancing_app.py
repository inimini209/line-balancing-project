import streamlit as st
import pandas as pd
from difflib import get_close_matches
import io

st.set_page_config(page_title="Line Balancing & Operator Rating", layout="wide")
st.title("Dynamic Line Balancing & Operator Efficiency Rating App (with Custom Combine & Delete)")

def combine_similar_operations(ob_df, sam_threshold=2.0, keywords=None):
    if keywords is None:
        keywords = ("IRON", "PRESS", "CUFF", "COLLAR", "YOKE", "LABEL")
    ob_df = ob_df.copy()
    used_idx = set()
    combined_rows = []
    combine_map = dict()
    for keyword in keywords:
        matches = ob_df[
            ob_df["OPERATION DESCRIPTION"].str.upper().str.contains(keyword)
            & ((ob_df["MACHINE SAM"].fillna(0) + ob_df["MANUAL SAM"].fillna(0)) < sam_threshold)
            & (~ob_df.index.isin(used_idx))
        ]
        for mtype in matches["MACHINE TYPE"].unique():
            m_matches = matches[matches["MACHINE TYPE"] == mtype]
            if len(m_matches) > 1:
                indices = m_matches.index
                used_idx.update(indices)
                combined_op_name = f"COMBINED {keyword} OPERATIONS ({mtype})"
                target = m_matches["TARGET"].iloc[0]
                sam_machine = m_matches["MACHINE SAM"].sum()
                sam_manual = m_matches["MANUAL SAM"].sum()
                combined_rows.append({
                    "OPERATION DESCRIPTION": combined_op_name,
                    "MACHINE SAM": sam_machine,
                    "MANUAL SAM": sam_manual,
                    "MACHINE TYPE": mtype,
                    "TARGET": target
                })
                combine_map[combined_op_name] = m_matches["OPERATION DESCRIPTION"].tolist()
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

def color_eff(val):
    try:
        val = float(val)
    except:
        return ""
    if val >= 95:
        return "background-color: #B6FFB0"   # Green
    elif val >= 85:
        return "background-color: #FFFFB0"   # Yellow
    elif val >= 75:
        return "background-color: #FFD580"   # Orange
    elif val >= 65:
        return "background-color: #FFB0B0"   # Light Red
    else:
        return "background-color: #FF4040; color: white"  # Red

st.sidebar.header("Upload Your Files")
skill_file = st.sidebar.file_uploader("Skill Matrix (.xlsx)", type="xlsx")
ob_file = st.sidebar.file_uploader("Operation Bulletin (.xlsx)", type="xlsx")

if skill_file and ob_file:
    skill_df = pd.read_excel(skill_file)
    ob_df = pd.read_excel(ob_file)

    skill_df.columns = [clean_string(col) for col in skill_df.columns]
    ob_df.columns = [clean_string(col) for col in ob_df.columns]
    ob_df["OPERATION DESCRIPTION"] = ob_df["OPERATION DESCRIPTION"].apply(clean_string)

    required_ob = {"OPERATION DESCRIPTION", "MACHINE TYPE", "TARGET", "MACHINE SAM", "MANUAL SAM"}
    if not required_ob.issubset(ob_df.columns):
        st.error(f"OB file must contain columns: {required_ob}")
        st.stop()
    if "OPERATOR NAME" not in skill_df.columns:
        st.error("Skill Matrix must contain column: OPERATOR NAME")
        st.stop()

    # Fuzzy mapping for OB → Skill Matrix
    skill_cols = [col for col in skill_df.columns if col != "OPERATOR NAME"]
    ob_ops = ob_df["OPERATION DESCRIPTION"].unique()
    OPERATION_MAP = {}
    FUZZY_LIST = []
    for op in ob_ops:
        if op not in skill_cols:
            suggestions = get_close_matches(op, skill_cols, n=1, cutoff=0.6)
            if suggestions:
                OPERATION_MAP[op] = suggestions[0]
                FUZZY_LIST.append((op, suggestions[0]))
            else:
                FUZZY_LIST.append((op, "NO SUGGESTION"))

    # -- Machine/combine tab state
    if "custom_combined" not in st.session_state:
        st.session_state["custom_combined"] = []
    if "ob_df_working" not in st.session_state:
        st.session_state["ob_df_working"], combine_map = combine_similar_operations(
            ob_df, sam_threshold=2.0, keywords=("IRON", "PRESS", "CUFF", "COLLAR", "YOKE", "LABEL")
        )
    else:
        base_df, combine_map = combine_similar_operations(
            ob_df, sam_threshold=2.0, keywords=("IRON", "PRESS", "CUFF", "COLLAR", "YOKE", "LABEL")
        )
        working_df = base_df.copy()
        for combo in st.session_state["custom_combined"]:
            working_df = working_df[~working_df["OPERATION DESCRIPTION"].isin(combo["ops"])]
            working_df = pd.concat([working_df, pd.DataFrame([combo["row"]])], ignore_index=True)
        st.session_state["ob_df_working"] = working_df

    ob_df2 = st.session_state["ob_df_working"]

    line_target = ob_df2["TARGET"].iloc[0]
    assignments = []
    assigned_operators = set()
    floater_candidates = set(skill_df["OPERATOR NAME"])

    for _, row in ob_df2.iterrows():
        ob_op_name = row["OPERATION DESCRIPTION"]
        skill_col = OPERATION_MAP.get(ob_op_name, ob_op_name)
        machine = row["MACHINE TYPE"]
        operator, efficiency = "NO SKILLED OP", 0

        if ob_op_name in combine_map:
            combined_cols = [OPERATION_MAP.get(c, c) for c in combine_map[ob_op_name]]
            effs = []
            for _, op_row in skill_df.iterrows():
                eff_list = [op_row[c] for c in combined_cols if c in skill_df.columns and not pd.isna(op_row[c])]
                if eff_list:
                    max_eff = max(eff_list)
                    effs.append((op_row["OPERATOR NAME"], max_eff))
            effs = [t for t in effs if t[0] not in assigned_operators and pd.notnull(t[1])]
            if effs:
                operator, efficiency = max(effs, key=lambda x: x[1])
                assigned_operators.add(operator)
            else:
                available_floaters = list(floater_candidates - assigned_operators)
                if available_floaters:
                    operator = available_floaters[0]
                    efficiency = 55
                    assigned_operators.add(operator)
                else:
                    operator, efficiency = "NO SKILLED OP", 55
        elif skill_col in skill_df.columns:
            candidates = skill_df[["OPERATOR NAME", skill_col]].dropna()
            candidates = candidates[~candidates["OPERATOR NAME"].isin(assigned_operators)]
            if not candidates.empty:
                best = candidates.loc[candidates[skill_col].idxmax()]
                operator = best["OPERATOR NAME"]
                efficiency = best[skill_col]
                assigned_operators.add(operator)
            else:
                available_floaters = list(floater_candidates - assigned_operators)
                if available_floaters:
                    operator = available_floaters[0]
                    efficiency = 55
                    assigned_operators.add(operator)
                else:
                    operator, efficiency = "NO SKILLED OP", 55
        else:
            available_floaters = list(floater_candidates - assigned_operators)
            if available_floaters:
                operator = available_floaters[0]
                efficiency = 55
                assigned_operators.add(operator)
            else:
                operator, efficiency = "NO SKILLED OP", 55

        try:
            eff_float = float(efficiency)
        except Exception:
            eff_float = 0
        actual_output = (eff_float / 100) * line_target

        assignments.append({
            "OPERATION":         ob_op_name,
            "MACHINE TYPE":      machine,
            "ASSIGNED OPERATOR": operator,
            "EFFICIENCY (%)":    eff_float,
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

    tabs = st.tabs(["Allocation & Output", "Operator Ratings", "Machine Summary", "Fuzzy Mapping"])

    with tabs[0]:
        st.header("Operation → Operator → Output")
        st.markdown(
            "<small>Color key: <span style='background:#B6FFB0;'>High</span> "
            "<span style='background:#FFFFB0;'>Medium</span> "
            "<span style='background:#FFD580;'>Average</span> "
            "<span style='background:#FFB0B0;'>Low</span> "
            "<span style='background:#FF4040;color:white;'>Very Low</span></small>", 
            unsafe_allow_html=True
        )
        styled_df = result_df.style.applymap(color_eff, subset=["EFFICIENCY (%)"])
        st.dataframe(styled_df, use_container_width=True)
        out_buffer = io.BytesIO()
        result_df.to_excel(out_buffer, index=False)
        st.download_button(
            label="⬇️ Download Allocation Table as Excel",
            data=out_buffer.getvalue(),
            file_name="operator_allocation.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with tabs[1]:
        st.header("Operator-wise Efficiency & Rating")
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
        st.header("Machine Type Summary")
        machine_summary = ob_df2["MACHINE TYPE"].value_counts().reset_index()
        machine_summary.columns = ["MACHINE TYPE", "OPERATIONS COUNT"]

        # Add grand total row at bottom
        total_row = pd.DataFrame({
            "MACHINE TYPE": ["TOTAL"],
            "OPERATIONS COUNT": [machine_summary["OPERATIONS COUNT"].sum()]
        })
        machine_summary = pd.concat([machine_summary, total_row], ignore_index=True)
        st.dataframe(machine_summary, use_container_width=True)

    with tabs[3]:
        st.header("Fuzzy Mapping (OB Operation → Skill Matrix Column)")
        for ob_op, match in FUZZY_LIST:
            st.write(f"**{ob_op}** → `{match}`")

        st.subheader("Manually Combine Operations (Same Machine Type Only)")
        op_options = [
            f"{op} [{mt}]" for op, mt in zip(ob_df2["OPERATION DESCRIPTION"], ob_df2["MACHINE TYPE"])
        ]
        op_map = {f"{op} [{mt}]": op for op, mt in zip(ob_df2["OPERATION DESCRIPTION"], ob_df2["MACHINE TYPE"])}
        mt_map = {f"{op} [{mt}]": mt for op, mt in zip(ob_df2["OPERATION DESCRIPTION"], ob_df2["MACHINE TYPE"])}

        combine_selected_display = st.multiselect(
            "Select operations to combine (must have the same machine type):",
            options=op_options,
            key="combine_ops"
        )
        combine_selected = [op_map[o] for o in combine_selected_display]

        custom_combine_name = st.text_input(
            "Give a name to this combined operation (e.g., 'CUSTOM COMBO 1')",
            key="combine_name"
        )

        valid_selection = True
        if len(combine_selected_display) > 1:
            machine_types = {mt_map[o] for o in combine_selected_display}
            if len(machine_types) > 1:
                valid_selection = False
                st.error(f"⚠️ Please select operations under the same machine type only. You selected: {machine_types}")

        if st.button("Combine Selected Operations"):
            if len(combine_selected) > 1 and custom_combine_name and valid_selection:
                mtype = mt_map[combine_selected_display[0]]
                subdf = ob_df2[ob_df2["OPERATION DESCRIPTION"].isin(combine_selected)]
                target = subdf["TARGET"].iloc[0]
                sam_machine = subdf["MACHINE SAM"].sum()
                sam_manual = subdf["MANUAL SAM"].sum()
                new_row = {
                    "OPERATION DESCRIPTION": custom_combine_name,
                    "MACHINE SAM": sam_machine,
                    "MANUAL SAM": sam_manual,
                    "MACHINE TYPE": mtype,
                    "TARGET": target
                }
                st.session_state["custom_combined"].append({
                    "ops": combine_selected,
                    "row": new_row
                })
                st.success(f"Combined {combine_selected_display} as '{custom_combine_name}' with machine type: {mtype}")
                st.experimental_rerun()
                st.stop()
            else:
                st.warning("Select at least two operations (of the same machine type) and give a name.")

        # ---- Delete Combined Operations ----
        if st.session_state["custom_combined"]:
            st.subheader("🗑️ Delete a Combined Operation")
            custom_names = [c["row"]["OPERATION DESCRIPTION"] for c in st.session_state["custom_combined"]]
            to_delete = st.selectbox("Select a combined operation to delete:", custom_names, key="delete_combo")
            if st.button("Delete Selected Combined Operation"):
                idx = custom_names.index(to_delete)
                st.session_state["custom_combined"].pop(idx)
                st.success(f"Deleted combined operation: {to_delete}. Underlying operations will now be available for re-combining.")
                st.experimental_rerun()
                st.stop()

        # ---- Show current operations table (after all combining) ----
        st.markdown("### Current Operations List (after all combining/deletion):")
        st.dataframe(ob_df2, use_container_width=True)

else:
    st.info("Please upload both the Skill Matrix and Operation Bulletin files.")
