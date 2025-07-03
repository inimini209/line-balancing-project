import streamlit as st
import pandas as pd
import numpy as np

st.title("🧵 Operator Assignment, Output & Rating Calculator")

# Upload files
skill_file = st.file_uploader("📥 Upload Skill Matrix (.xlsx)", type="xlsx")
ob_file = st.file_uploader("📥 Upload Operation Bulletin (.xlsx)", type="xlsx")

def assign_rating(eff):
    if pd.isna(eff):
        return np.nan
    if eff < 65:
        return 1
    elif eff < 75:
        return 2
    elif eff < 85:
        return 3
    elif eff < 95:
        return 4
    else:
        return 5

if skill_file and ob_file:
    # Read and clean Skill Matrix
    skill_df = pd.read_excel(skill_file)
    skill_df.columns = [col.strip().upper() for col in skill_df.columns]
    skill_cols = [col for col in skill_df.columns if col not in ['S.NO.', 'OPERATOR NAME', 'CARD NO']]
    skill_df['EFFICIENCY'] = skill_df[skill_cols].apply(pd.to_numeric, errors='coerce').mean(axis=1)
    eff_df = skill_df[['OPERATOR NAME', 'EFFICIENCY']].dropna().sort_values('EFFICIENCY', ascending=False).reset_index(drop=True)

    # Read and clean Operation Bulletin
    ob_df = pd.read_excel(ob_file)
    ob_df.columns = [col.strip().upper() for col in ob_df.columns]
    ob_df['SAM'] = pd.to_numeric(ob_df['SAM'], errors='coerce')
    ob_df['TARGET OUTPUT'] = pd.to_numeric(ob_df['TARGET OUTPUT'], errors='coerce')

    # Sort operations by SAM (descending) - or change this to another logic if needed
    ob_df = ob_df.sort_values('SAM', ascending=False).reset_index(drop=True)

    # Assign operators to operations by efficiency
    operators = eff_df['OPERATOR NAME'].tolist()
    operator_eff_map = dict(zip(eff_df['OPERATOR NAME'], eff_df['EFFICIENCY']))
    n_ops = len(operators)
    ob_df['ASSIGNED OPERATOR'] = [operators[i % n_ops] for i in range(len(ob_df))]
    ob_df['OPERATOR EFFICIENCY'] = ob_df['ASSIGNED OPERATOR'].map(operator_eff_map)

    # Calculate actual output and rating
    ob_df['ACTUAL OUTPUT'] = ob_df['TARGET OUTPUT'] * (ob_df['OPERATOR EFFICIENCY'] / 100)
    ob_df['OPERATION EFFICIENCY (%)'] = (ob_df['ACTUAL OUTPUT'] / ob_df['TARGET OUTPUT']) * 100
    ob_df['RATING'] = ob_df['OPERATION EFFICIENCY (%)'].apply(assign_rating)

    st.subheader("Operator Assignment, Output & Rating")
    st.dataframe(ob_df[['OPERATION DESCRIPTION', 'SAM', 'MACHINE TYPE', 'ASSIGNED OPERATOR', 'OPERATOR EFFICIENCY', 'TARGET OUTPUT', 'ACTUAL OUTPUT', 'OPERATION EFFICIENCY (%)', 'RATING']])

else:
    st.info("Please upload both the Skill Matrix and Operation Bulletin files.")
