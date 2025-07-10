import streamlit as st
import pandas as pd
from difflib import get_close_matches
import io

st.set_page_config(page_title="Line Balancing Prototype", layout="wide")
st.title("Line Balancing & Operator Allocation Prototype")

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
        return "background-color: #B6FFB0"
    elif val >= 85:
        return "background-color: #FFFFB0"
    elif val >= 75:
        return "background-color: #FFD580"
    elif val >= 65:
        return "background-color: #FFB0B0"
    else:
        return "background-color: #FF4040; color: white"

def rate(e):
    if e < 65: return 1
    if e < 75: return 2
    if e < 85: return 3
    if e < 95: return 4
    return 5

def get_combinable_suggestions(ob_df, sam_threshold=2.0):
    # Visual: group by machine type and low SAM for suggestion only
    suggestions = []
    for mtype, group in ob_df.groupby("MACHINE TYPE"):
        low_sam = group[group["MACHINE SAM"].fillna(0) + group["MANUAL SAM"].fillna(0) < sam_threshold]
        if len(low_sam) > 1:
            suggestions.append((mtype, low_sam["OPERATION DESCRIPTION"].tolist()))
    return suggestions

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

    ob_df = ob_df.dropna(how="all")
    ob_df = ob_df.reset_index(drop=True)
    ob_df["OB_ORDER"] = ob_df.index  # Always keep for restoring order

    # Fuzzy mapping for OB → Skill Matrix
    skill_cols = [col for col in skill_df.columns if col != "OPERATOR NAME"]
    ob_ops = ob_df["OPERATION DESCRIPTION"].unique()
    OPERATION_MAP = {}
    for op in ob_ops:
        if op not in skill_cols:
            suggestions = get_close_matches(op, skill_cols, n=1, cutoff=0.6)
            if suggestions:
                OPERATION_MAP[op] = suggestions[0]
            else:
                OPERATION_MAP[op] = op
        else:
            OPERATION_MAP[op] = op

    # -------------------------
    # Assign operators: sort by highest SAM first, then OB order
    ob_df["SAM_TOTAL"] = ob_df["MACHINE SAM"].fillna(0) + ob_df["MANUAL SAM"].fillna(0)
    ob_sorted = ob_df.sort_values(by=["SAM_TOTAL", "OB_ORDER"], ascending=[False, True]).copy()
    operators = list(skill_df["OPERATOR NAME"])
    assigned_ops = []
    op_allocation = {}

    # Allocate operators to highest SAM first (no repeats)
    for idx, row in ob_sorted.iterrows():
        op_desc = row["OPERATION DESCRIPTION"]
        skill_col = OPERATION_MAP[op_desc]
        skill_vals = skill_df[["OPERATOR NAME", skill_col]].dropna()
        skill_vals = skill_vals[~skill_vals["OPERATOR NAME"].isin(assigned_ops)]
        if not skill_vals.empty:
            best = skill_vals.loc[skill_vals[skill_col].idxmax()]
            assigned_ops.append(best["OPERATOR NAME"])
            op_allocation[op_desc] = (best["OPERATOR NAME"], best[skill_col])
        else:
            # Floater logic, 55% efficiency
            unassigned = [op for op in operators if op not in assigned_ops]
            if unassigned:
                op_allocation[op_desc] = (unassigned[0], 55)
                assigned_ops.append(unassigned[0])
            else:
                op_allocation[op_desc] = ("NO SKILLED OP", 55)

    # Restore OB display order for table output
    display_rows = []
    line_target = ob_df["TARGET"].iloc[0]
    for _, row in ob_df.sort_values("OB_ORDER").iterrows():
        op_desc = row["OPERATION DESCRIPTION"]
        operator, eff = op_allocation.get(op_desc, ("NO SKILLED OP", 55))
        actual_output = (float(eff)/100) * line_target
        display_rows.append({
            "OPERATION": op_desc,
            "MACHINE TYPE": row["MACHINE TYPE"],
            "ASSIGNED OPERATOR": operator,
            "EFFICIENCY (%)": eff,
            "TARGET": row["TARGET"],
            "ACTUAL OUTPUT": actual_output,
            "RATING": rate(eff)
        })
    display_df = pd.DataFrame(display_rows)

    # ----------- Machine Summary with Total -----------
    machine_summary = display_df["MACHINE TYPE"].value_counts().reset_index()
    machine_summary.columns = ["MACHINE TYPE", "OPERATIONS COUNT"]
    total_row = pd.DataFrame([{"MACHINE TYPE": "TOTAL", "OPERATIONS COUNT": machine_summary["OPERATIONS COUNT"].sum()}])
    machine_summary = pd.concat([machine_summary, total_row], ignore_index=True)

    # ----------------- Manual Combine -----------------
    if "custom_combined" not in st.session_state:
        st.session_state["custom_combined"] = []
    if "ob_df_working" not in st.session_state or st.session_state.get("reset_ob_working", False):
        ob_base_df = ob_df.copy()
        working_df = ob_base_df.copy()
        manual_combo_count = 0
        max_order = working_df["OB_ORDER"].max() if not working_df.empty else 0
        for combo in st.session_state["custom_combined"]:
            to_remove = combo["ops"]
            working_df = working_df[~working_df["OPERATION DESCRIPTION"].isin(to_remove)]
            new_row = combo["row"].copy()
            manual_combo_count += 1
            new_row["OB_ORDER"] = max_order + manual_combo_count
            working_df = pd.concat([working_df, pd.DataFrame([new_row])], ignore_index=True)
        working_df = working_df.sort_values("OB_ORDER").reset_index(drop=True)
        st.session_state["ob_df_working"] = working_df
        st.session_state["reset_ob_working"] = False
    else:
        working_df = st.session_state["ob_df_working"]

    # ----------------------- UI Tabs ---------------------
    tabs = st.tabs(["Allocation & Output", "Operator Ratings", "Machine Summary", "Fuzzy Suggestions", "Manual Combine"])

    with tabs[0]:
        st.header("Operator Allocation and Output (OB Order)")
        styled_df = display_df.style.applymap(color_eff, subset=["EFFICIENCY (%)"])
        st.dataframe(styled_df, use_container_width=True)
        out_buffer = io.BytesIO()
        display_df.to_excel(out_buffer, index=False)
        st.download_button(
            label="⬇️ Download Allocation Table as Excel",
            data=out_buffer.getvalue(),
            file_name="operator_allocation.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with tabs[1]:
        st.header("Operator-wise Efficiency & Rating")
        op_summary = display_df.groupby("ASSIGNED OPERATOR", dropna=False).agg({
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
        st.dataframe(machine_summary, use_container_width=True)

    with tabs[3]:
        st.header("Fuzzy Suggestions for Combinable Operations")
        suggestions = get_combinable_suggestions(ob_df)
        if not suggestions:
            st.info("No combinable operations found under default suggestion logic.")
        else:
            for mtype, ops in suggestions:
                st.markdown(f"<b>{mtype}</b>: {', '.join(ops)}", unsafe_allow_html=True)

    with tabs[4]:
        st.header("Manually Combine Operations (Same Machine Type Only)")
        op_options = [
            f"{op} [{mt}]" for op, mt in zip(working_df["OPERATION DESCRIPTION"], working_df["MACHINE TYPE"])
        ]
        op_map = {f"{op} [{mt}]": op for op, mt in zip(working_df["OPERATION DESCRIPTION"], working_df["MACHINE TYPE"])}
        mt_map = {f"{op} [{mt}]": mt for op, mt in zip(working_df["OPERATION DESCRIPTION"], working_df["MACHINE TYPE"])}

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
                st.error(f"Please select operations under the same machine type only. You selected: {machine_types}")

        if st.button("Combine Selected Operations"):
            if len(combine_selected) > 1 and custom_combine_name and valid_selection:
                mtype = mt_map[combine_selected_display[0]]
                subdf = working_df[working_df["OPERATION DESCRIPTION"].isin(combine_selected)]
                target = subdf["TARGET"].iloc[0]
                sam_machine = subdf["MACHINE SAM"].sum()
                sam_manual = subdf["MANUAL SAM"].sum()
                max_order = working_df["OB_ORDER"].max() if not working_df.empty else 0
                manual_combo_orders = [row["OB_ORDER"] for row in st.session_state["custom_combined"]] if st.session_state["custom_combined"] else []
                next_manual_order = max_order + len(manual_combo_orders) + 1
                new_row = {
                    "OPERATION DESCRIPTION": custom_combine_name,
                    "MACHINE SAM": sam_machine,
                    "MANUAL SAM": sam_manual,
                    "MACHINE TYPE": mtype,
                    "TARGET": target,
                    "OB_ORDER": next_manual_order
                }
                st.session_state["custom_combined"].append({
                    "ops": combine_selected,
                    "row": new_row
                })
                st.session_state["reset_ob_working"] = True
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
                st.session_state["reset_ob_working"] = True
                st.success(f"Deleted combined operation: {to_delete}. Underlying operations will now be available for re-combining.")
                st.experimental_rerun()
                st.stop()

        # ---- Show current operations table (after all combining/deletion) ----
        st.markdown("### Current Operations List (after all combining/deletion):")
        st.dataframe(working_df.sort_values("OB_ORDER"), use_container_width=True)

else:
    st.info("Please upload both the Skill Matrix and Operation Bulletin files.")
