import streamlit as st
import pandas as pd

st.title("🧵 Dynamic Line Balancing & Efficiency Rating App")

# Tabs for sections
tab1, tab2, tab3, tab4 = st.tabs(["📥 Upload Files", "⚙️ Efficiency & Rating", "📊 Line Balancing", "🛠️ Machine Summary"])

with tab1:
    st.header("📥 Upload Files")

    skill_file = st.file_uploader("Upload Skill Matrix (.xlsx)", type=["xlsx"])
    ob_file = st.file_uploader("Upload Operation Bulletin (.xlsx)", type=["xlsx"])

    if skill_file:
        skill_df = pd.read_excel(skill_file)
        skill_df.columns = skill_df.columns.str.replace('\n', ' ', regex=True).str.strip().str.upper()
        st.subheader("Skill Matrix Preview")
        st.dataframe(skill_df)

    if ob_file:
        ob_df = pd.read_excel(ob_file)
        ob_df.columns = ob_df.columns.str.replace('\n', ' ', regex=True).str.strip().str.upper()
        st.subheader("Operation Bulletin Preview")
        st.dataframe(ob_df)

with tab2:
    st.header("⚙️ Efficiency & Rating")

    if ob_file:
        ob_df['EFFICIENCY (%)'] = (ob_df['ACTUAL OUTPUT'] / ob_df['TARGET']) * 100

        def get_rating(eff):
            if eff < 65:
                return 1
            elif 65 <= eff < 75:
                return 2
            elif 75 <= eff < 85:
                return 3
            elif 85 <= eff < 95:
                return 4
            else:
                return 5

        ob_df['RATING'] = ob_df['EFFICIENCY (%)'].apply(get_rating)

        st.subheader("Efficiency & Rating Results")
        st.dataframe(ob_df[['OPERATION DESCRIPTION', 'TARGET', 'ACTUAL OUTPUT', 'EFFICIENCY (%)', 'RATING']])

with tab3:
    st.header("📊 Automatic Line Balancing (by Skill Matrix)")

    if skill_file and ob_file:
        balanced_df = ob_df[['OPERATION DESCRIPTION', 'MACHINE TYPE']].copy()
        assigned_operators = []

        # Copy of skill matrix for assignment
        skill_df_copy = skill_df.copy()

        for index, row in balanced_df.iterrows():
            machine_type = row['MACHINE TYPE']

            # Find available operators with highest skill for this machine type
            if machine_type in skill_df_copy.columns:
                best_operator_row = skill_df_copy.loc[skill_df_copy[machine_type].idxmax()]
                best_operator_name = best_operator_row['OPERATOR NAME']
                assigned_operators.append(best_operator_name)

                # Remove this operator from availability by setting their skill to -1
                skill_df_copy.loc[skill_df_copy['OPERATOR NAME'] == best_operator_name, machine_type] = -1
            else:
                assigned_operators.append("Not Available")

        balanced_df['ASSIGNED OPERATOR'] = assigned_operators

        st.subheader("Optimal Operator - Operation Allocation")
        st.dataframe(balanced_df)


with tab4:
    st.header("🛠️ Machine Summary")
    if ob_file:
        machine_summary = ob_df['MACHINE TYPE'].value_counts().reset_index()
        machine_summary.columns = ['MACHINE TYPE', 'QUANTITY NEEDED']

        st.subheader("Number of Machines Needed by Type")
        st.dataframe(machine_summary)

