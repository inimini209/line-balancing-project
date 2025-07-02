import streamlit as st
import pandas as pd

st.title("Dynamic Line Balancing App (Prototype)")

# Upload skill matrix file
skill_file = st.file_uploader("Upload Skill Matrix (.xlsx)", type=["xlsx"])
# Upload operation bulletin file
ob_file = st.file_uploader("Upload Operation Bulletin (.ods)", type=["ods"])

if skill_file and ob_file:
    # Read Skill Matrix
    skill_df = pd.read_excel(skill_file)
    skill_df.columns = skill_df.columns.str.strip().str.upper()

    # Read Operation Bulletin (header on 2nd row → header=1)
    ob_df = pd.read_excel(ob_file, engine='odf', sheet_name=0, header=1)
    ob_df.columns = ob_df.columns.str.strip().str.upper()

    st.subheader("Skill Matrix Data")
    st.dataframe(skill_df)

    st.subheader("Operation Bulletin Data")
    st.dataframe(ob_df)

    # Check actual columns present
    st.write("Operation Bulletin Columns:", ob_df.columns.tolist())

    # Select relevant columns (adjusted to actual names from your file)
    ob_df = ob_df[['SR. NO.', 'OPERATION DESCRIPTION', 'MACHINESAM', 'MACHINETYPE']]

    # Simple productivity summary mockup for now
    st.subheader("Basic Summary")
    total_sam = ob_df['MACHINESAM'].sum()
    st.write(f"Total SAM (Machine SAM): {total_sam:.2f} minutes")

    unique_machines = ob_df['MACHINETYPE'].nunique()
    st.write(f"Total unique machine types needed: {unique_machines}")

    # Show machine type list
    st.write("Machine Types Required:")
    st.dataframe(ob_df['MACHINETYPE'].value_counts().reset_index().rename(columns={'index': 'Machine Type', 'MACHINETYPE': 'Quantity'}))

else:
    st.warning("Please upload both the Skill Matrix and Operation Bulletin files.")

