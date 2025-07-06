import streamlit as st
import pandas as pd
from difflib import get_close_matches

st.title("🔗 OB–Skill Matrix Auto-Mapping (Fuzzy Suggestions)")

skill_file = st.file_uploader("Upload Skill Matrix (.xlsx)", type="xlsx")
ob_file    = st.file_uploader("Upload Operation Bulletin (.xlsx)", type="xlsx")

def clean_string(s):
    if pd.isnull(s): return ""
    return (str(s)
            .replace('\n', ' ')
            .replace('\r', ' ')
            .replace('\t', ' ')
            .replace('  ', ' ')
            .strip()
            .upper())

if skill_file and ob_file:
    skill_df = pd.read_excel(skill_file)
    ob_df = pd.read_excel(ob_file)

    # Get Skill Matrix columns except the operator name column
    skill_cols = [clean_string(col) for col in skill_df.columns if "OPERATOR" not in col]
    ob_ops = [clean_string(op) for op in ob_df["OPERATION DESCRIPTION"].unique()]

    st.subheader("Skill Matrix Columns (cleaned)")
    st.write(skill_cols)
    st.subheader("OB Operation Descriptions (cleaned)")
    st.write(ob_ops)

    missing_ops = []
    fuzzy_map = {}
    auto_map = {}
    for op in ob_ops:
        if op not in skill_cols:
            missing_ops.append(op)
            suggestions = get_close_matches(op, skill_cols, n=1, cutoff=0.6)
            fuzzy_map[op] = suggestions
            if suggestions:
                auto_map[op] = suggestions[0]
    if missing_ops:
        st.warning("OB operations with **NO exact match** in Skill Matrix columns (see auto-mapping below):")
        for op in missing_ops:
            st.write(f"**{op}**")
            suggestions = fuzzy_map[op]
            if suggestions:
                st.write(" &rarr; Fuzzy suggestion(s): ", suggestions)
            else:
                st.write(" &rarr; No close match found.")

        st.subheader("Auto-generated OPERATION_MAP (copy and paste this):")
        st.code("OPERATION_MAP = " + str(auto_map), language="python")
    else:
        st.success("🎉 All OB operations match exactly with Skill Matrix columns!")

    # If you want to see the full mapping (including exact matches):
    # full_map = {op: (op if op in skill_cols else (auto_map.get(op, ""))) for op in ob_ops}
    # st.subheader("Full mapping (including exact matches):")
    # st.code("OPERATION_MAP = " + str(full_map), language="python")
else:
    st.info("Please upload BOTH the Skill Matrix and Operation Bulletin files.")
