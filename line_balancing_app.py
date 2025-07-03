import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dynamic Line Balancing & Operator Rating App", layout="wide")

st.title("🧵 Dynamic Line Balancing & Operator Rating App")

# Upload files
st.sidebar.header("📥 Upload Files")
skill_file = st.sidebar.file_uploader("Upload Skill Matrix (.xlsx)", type="xlsx")
ob_file = st.sidebar.file_uploader("Upload Operation Bulletin (.xlsx)", type="xlsx")

if skill_file and ob_file:
    skill_df = pd.read_excel(skill_file)
    ob_df = pd.read_excel(ob_file)

    # Clean Operation Bulletin columns
    ob_df.columns = [col.strip() for col in ob_df.columns]

    st.sidebar.success("✅ Files uploaded successfully!")

    tabs = st.tabs(["📊 Line Balancing", "⚙️ Efficiency & Rating", "🛠️ Machine Summary"])

    with tabs[0]:
        st.header("📊 Line Balancing")

        # Get operator list
        operators = skill_df["OPERATOR NAME"].tolist()

        # List of operations in OB
        operations = ob_df["OPERATION DESCRIPTION"].tolist()

        assignments = []
        for operation in operations:
            if operation in skill_df.columns:
                best_operator = (
                    skill_df[["OPERATOR NAME", operation]]
                    .dropna()
                    .sort_values(by=operation, ascending=False)
                    .iloc[0]
                )
                assignments.append(
                    {
                        "OPERATION DESCRIPTION": operation,
                        "MACHINE TYPE": ob_df.loc[ob_df["OPERATION DESCRIPTION"] == operation, "MACHINE TYPE"].values[0],
                        "ASSIGNED OPERATOR": best_operator["OPERATOR NAME"],
                        "EFFICIENCY (%)": best_operator[operation],
                    }
                )
            else:
                assignments.append(
                    {
                        "OPERATION DESCRIPTION": operation,
                        "MACHINE TYPE": ob_df.loc[ob_df["OPERATION DESCRIPTION"] == operation, "MACHINE TYPE"].values[0],
                        "ASSIGNED OPERATOR": "Not Skilled",
                        "EFFICIENCY (%)": 0,
                    }
                )

        balanced_df = pd.DataFrame(assignments)

        st.dataframe(balanced_df, use_container_width=True)
        st.session_state["balanced_df"] = balanced_df

    with tabs[1]:
        st.header("⚙️ Operator-wise Efficiency & Rating")

        if "balanced_df" in st.session_state:
            balanced_df = st.session_state["balanced_df"].copy()
            target_value = ob_df["TARGET"].iloc[0]

            balanced_df["ACTUAL OUTPUT"] = (balanced_df["EFFICIENCY (%)"] / 100) * target_value

            operator_summary = balanced_df.groupby("ASSIGNED OPERATOR").agg(
                {
                    "EFFICIENCY (%)": "mean",
                    "ACTUAL OUTPUT": "sum",
                }
            ).reset_index()

            # Rating logic
            def assign_rating(eff):
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

            operator_summary["RATING"] = operator_summary["EFFICIENCY (%)"].apply(assign_rating)

            st.dataframe(operator_summary, use_container_width=True)
        else:
            st.warning("Please complete Line Balancing first.")

    with tabs[2]:
        st.header("🛠️ Machine Type Summary")

        machine_summary = ob_df["MACHINE TYPE"].value_counts().reset_index()
        machine_summary.columns = ["MACHINE TYPE", "NUMBER OF OPERATIONS"]

        st.dataframe(machine_summary, use_container_width=True)

else:
    st.info("👈 Please upload both Skill Matrix and Operation Bulletin to begin.")
