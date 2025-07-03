import streamlit as st
import pandas as pd

st.title("🧵 Dynamic Line Balancing & Operator Efficiency Rating App")

# Upload Skill Matrix
skill_file = st.file_uploader("📥 Upload Skill Matrix (.xlsx)", type="xlsx")

# Upload Operation Bulletin
ob_file = st.file_uploader("📥 Upload Operation Bulletin (.xlsx)", type="xlsx")

if skill_file and ob_file:

    # Read and clean Skill Matrix
    skill_df = pd.read_excel(skill_file)
    skill_df.columns = [col.strip().upper() for col in skill_df.columns]
    st.subheader("Skill Matrix Columns:")
    st.write(skill_df.columns.tolist())

    # Read and clean Operation Bulletin
    ob_df = pd.read_excel(ob_file)
    ob_df.columns = [col.strip().upper() for col in ob_df.columns]
    st.subheader("Operation Bulletin Columns:")
    st.write(ob_df.columns.tolist())

    try:
        # Operator list
        operators = skill_df["OPERATOR NAME"].tolist()

        st.header("⚙️ Operator Efficiency & Ratings")

        # Assuming 'ACTUAL OUTPUT' and 'TARGET OUTPUT' columns exist in OB
        ob_df["EFFICIENCY (%)"] = (ob_df["ACTUAL OUTPUT"] / ob_df["TARGET OUTPUT"]) * 100

        def assign_rating(eff):
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

        ob_df["RATING"] = ob_df["EFFICIENCY (%)"].apply(assign_rating)

        st.dataframe(ob_df[["OPERATION DESCRIPTION", "ACTUAL OUTPUT", "TARGET OUTPUT", "EFFICIENCY (%)", "RATING"]])

        st.header("📊 Line Balancing (Sample)")

        # Simple assignment of operators to operations (example — replace with your logic)
        balanced_df = ob_df[["OPERATION DESCRIPTION", "MACHINE TYPE"]].copy()
        balanced_df["ASSIGNED OPERATOR"] = [operators[i % len(operators)] for i in range(len(balanced_df))]

        st.dataframe(balanced_df)

        st.header("🛠️ Machine Summary")

        machine_summary = ob_df["MACHINE TYPE"].value_counts().reset_index()
        machine_summary.columns = ["MACHINE TYPE", "QUANTITY NEEDED"]

        st.dataframe(machine_summary)

    except KeyError as e:
        st.error(f"Missing expected column: {e}")

else:
    st.warning("👆 Please upload both the Skill Matrix and Operation Bulletin files.")
