import streamlit as st
import pandas as pd
from difflib import get_close_matches

st.set_page_config(page_title="Line Balancing & Operator Rating", layout="wide")
st.title("🧵 Dynamic Line Balancing & Operator Efficiency Rating App (with Fuzzy Mapping & Floaters)")

def combine_similar_operations(ob_df, sam_threshold=2.0, keywords=None):
    # keywords: tuple/list of grouping words
    if keywords is None:
        keywords = ("IRON", "PRESS", "CUFF", "COLLAR", "YOKE", "LABEL")
    ob_df = ob_df.copy()
    used_idx = set()
    combined_rows = []
    combine_map = dict()
    for keyword in keywords:
        # Find all operations for this keyword under the sam threshold
        matches = ob_df[
            ob_df["OPERATION DESCRIPTION"].str.upper().str.contains(keyword)
            & ((ob_df["MACHINE SAM"].fillna(0) + ob_df["MANUAL SAM"].fillna(0)) < sam_threshold)
            & (~ob_df.index.isin(used_idx))
        ]
        if len(matches) > 1:
            # For each unique machine type, only combine if more than 1 with that type and keyword
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

st.sidebar.header("📥 Upload Your Files")
skill_file = st.sidebar.file_uploader("Skill Matrix (.xlsx)", type="xlsx")
ob_file    = st.sidebar.file_uploader("Operation Bulletin (.xlsx)", type="xlsx")

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

    # Build OPERATION_MAP using fuzzy matching
    skill_cols = [col for col in skill_df.columns if col != "OPERATOR NAME"]
