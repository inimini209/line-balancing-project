import streamlit as st
import pandas as pd
import numpy as np

st.title("🧵 Dynamic Line Balancing & Operator Efficiency Platform")

# Upload files
skill_file = st.file_uploader("📥 Upload Skill Matrix (.xlsx)", type="xlsx")
ob_file = st.file_uploader("📥 Upload Operation Bulletin (.xlsx)", type="xlsx")

def calculate_efficiency_and_rating(skill_df):
    # Assume all columns after OPERATOR NAME are skill columns (efficiency %)
    skill_cols = [col for col in skill_df.columns if col not in ['S.NO.', 'OPERATOR NAME', 'CARD NO']]
    skill_df['EFFICIENCY'] = skill_df[skill_cols].apply(pd.to_numeric, errors='coerce').mean(axis=1)
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
    skill_df['RATING'] = skill_df['EFFICIENCY'].apply(assign_rating)
    return skill_df[['OPERATOR NAME', 'EFFICIENCY', 'RATING']]

def club_operations(df, sam_threshold=1.0, custom_club_map=None):
    # Club operations with SAM <= threshold and similar operation (by custom map or keywords)
    df = df.copy()
    df['CLUB_KEY'] = df['OPERATION DESCRIPTION']
    # Example: club ironing operations
    if custom_club_map is None:
        custom_club_map = {
            'IRON': ['IRON', 'PRESS', 'IRONING'],
            'CUFF': ['CUFF'],
            'COLLAR': ['COLLAR'],
        }
    def get_club_key(desc):
        desc_upper = desc.upper()
        for key, keywords in custom_club_map.items():
            if any(kw in desc_upper for kw in keywords):
                return key
        return desc
    df['CLUB_KEY'] = df['OPERATION DESCRIPTION'].apply(get_club_key)
    # Club only low SAM
    low_sam = df['SAM'] <= sam_threshold
    clubbed = (
        df[low_sam]
        .groupby(['CLUB_KEY', 'MACHINE TYPE'])
        .agg({
            'SAM': 'sum',
            'TARGET OUTPUT': 'sum',
            'ACTUAL OUTPUT': 'sum',
            'OPERATION DESCRIPTION': lambda x: " + ".join(x),
        })
        .reset_index()
        .rename(columns={'OPERATION DESCRIPTION': 'COMBINED OPERATIONS'})
    )
    # Keep other operations as is
    others = df[~low_sam].copy()
    others['COMBINED OPERATIONS'] = others['OPERATION DESCRIPTION']
    # Merge
    final_df = pd.concat([
        clubbed[['COMBINED OPERATIONS', 'MACHINE TYPE', 'SAM', 'TARGET OUTPUT', 'ACTUAL OUTPUT']],
        others[['COMBINED OPERATIONS', 'MACHINE TYPE', 'SAM', 'TARGET OUTPUT', 'ACTUAL OUTPUT']]
    ], ignore_index=True)
    return final_df

if skill_file and ob_file:
    # Read and clean Skill Matrix
    skill_df = pd.read_excel(skill_file)
    skill_df.columns = [col.strip().upper() for col in skill_df.columns]
    skill_df = skill_df.dropna(how='all', axis=1).dropna(how='all', axis=0)
    # Read and clean Operation Bulletin
    ob_df = pd.read_excel(ob_file)
    ob_df.columns = [col.strip().upper() for col in ob_df.columns]
    ob_df = ob_df.dropna(how='all', axis=1).dropna(how='all', axis=0)

    # Calculate operator efficiency and rating
    eff_df = calculate_efficiency_and_rating(skill_df)
    st.subheader("Operator Efficiency & Rating")
    st.dataframe(eff_df)

    # Assign operators to operations based on efficiency (highest first)
    eff_sorted = eff_df.sort_values('EFFICIENCY', ascending=False)
    operators = eff_sorted['OPERATOR NAME'].tolist()
    operator_eff_map = dict(zip(eff_sorted['OPERATOR NAME'], eff_sorted['EFFICIENCY']))
    operator_rating_map = dict(zip(eff_sorted['OPERATOR NAME'], eff_sorted['RATING']))

    # Assign operators in a round-robin, highest efficiency first
    ob_df = ob_df.copy()
    n_ops = len(operators)
    ob_df['ASSIGNED OPERATOR'] = [operators[i % n_ops] for i in range(len(ob_df))]
    ob_df['OPERATOR EFFICIENCY'] = ob_df['ASSIGNED OPERATOR'].map(operator_eff_map)
    ob_df['OPERATOR RATING'] = ob_df['ASSIGNED OPERATOR'].map(operator_rating_map)

    # Calculate actual output for each operation
    ob_df['TARGET OUTPUT'] = pd.to_numeric(ob_df['TARGET OUTPUT'], errors='coerce')
    ob_df['SAM'] = pd.to_numeric(ob_df['SAM'], errors='coerce')
    ob_df['ACTUAL OUTPUT'] = ob_df['TARGET OUTPUT'] * (ob_df['OPERATOR EFFICIENCY'] / 100)

    st.subheader("Line Balancing (Operator Assignment & Output)")
    st.dataframe(ob_df[['OPERATION DESCRIPTION', 'SAM', 'MACHINE TYPE', 'ASSIGNED OPERATOR', 'OPERATOR EFFICIENCY', 'OPERATOR RATING', 'TARGET OUTPUT', 'ACTUAL OUTPUT']])

    # Club similar low-SAM operations
    st.subheader("Clubbed Low-SAM Similar Operations")
    sam_threshold = st.number_input("SAM threshold for clubbing (minutes):", min_value=0.1, value=1.0, step=0.1)
    clubbed_df = club_operations(ob_df, sam_threshold=sam_threshold)
    st.dataframe(clubbed_df)

    # Machine summary
    st.subheader("Machine Requirement Summary")
    machine_summary = clubbed_df['MACHINE TYPE'].value_counts().reset_index()
    machine_summary.columns = ['MACHINE TYPE', 'QUANTITY NEEDED']
    st.dataframe(machine_summary)

else:
    st.info("Please upload both the Skill Matrix and Operation Bulletin files.")

