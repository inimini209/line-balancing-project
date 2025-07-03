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
        skill_df.columns = skill_df.columns.str.strip().str.upper()
        st.subheader("Skill Matrix Preview")
        st.dataframe(skill_df)

    if ob_file:
        ob_df = pd.read_excel(ob_file)
        ob_df.columns = ob_df.columns.str.strip().str.upper()
        st.write(ob_df.columns.tolist())
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
    st.header("📊 Automatic Line Balancing (Prototype)")

    if skill_file and ob_file:
        # For now, basic matching: same number of operators as operations
        balanced_df = ob_df[['OPERATION DESCRIPTION', 'MACHINE TYPE']].copy()
        balanced_df['ASSIGNED OPERATOR'] = ['Operator ' + str(i+1) for i in range(len(balanced_df))]

        st.subheader("Operator - Operation Allocation")
        st.dataframe(balanced_df)

with tab4:
    st.header("🛠️ Machine Summary")

    if ob_file:
        machine_summary = ob_df['MACHINE TYPE'].value_counts().reset_index()
        machine_summary.columns = ['MACHINE TYPE', 'QUANTITY NEEDED']

        st.subheader("Number of Machines Needed by Type")
        st.dataframe(machine_summary)
