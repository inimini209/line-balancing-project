import streamlit as st
import pandas as pd

st.title("🧵 Dynamic Line Balancing & Operator Efficiency Assignment")

# Upload files
skill_file = st.file_uploader("📥 Upload Skill Matrix (.xlsx)", type="xlsx")
ob_file = st.file_uploader("📥 Upload Operation Bulletin (.xlsx)", type="xlsx")

if skill_file and ob_file:
    # Read and clean Skill Matrix
    skill_df = pd.read_excel(skill_file)
    skill_df.columns = [str(col).strip().upper() for col in skill_df.columns]
    skill_df = skill_df.dropna(how='all', axis=1).dropna(how='all', axis=0)

    # Read and clean Operation Bulletin
    ob_df = pd.read_excel(ob_file)
    ob_df.columns = [str(col).strip().upper() for col in ob_df.columns]
    ob_df = ob_df.dropna(how='all', axis=1).dropna(how='all', axis=0)

    try:
        # Calculate average efficiency for each operator
        operator_col = 'OPERATOR NAME'
        skill_cols = skill_df.columns[3:]  # Skip S.NO., OPERATOR NAME, CARD NO
        operator_eff = skill_df.set_index(operator_col)[skill_cols].apply(pd.to_numeric, errors='coerce').mean(axis=1)
        operator_eff = operator_eff.dropna().sort_values(ascending=False)

        # Assign operators to operations by descending efficiency
        assigned_ops = operator_eff.index.tolist()
        num_ops = len(assigned_ops)
        ob_df['ASSIGNED OPERATOR'] = [assigned_ops[i % num_ops] for i in range(len(ob_df))]
        ob_df['OPERATOR EFFICIENCY'] = [operator_eff.get(op, 0) for op in ob_df['ASSIGNED OPERATOR']]

        # Calculate actual output
        ob_df['TARGET OUTPUT'] = pd.to_numeric(ob_df['TARGET'], errors='coerce')
        ob_df['ACTUAL OUTPUT'] = ob_df['TARGET OUTPUT'] * (ob_df['OPERATOR EFFICIENCY'] / 100)

        st.header("⚙️ Operator Assignment and Actual Output")
        st.dataframe(ob_df[['OPERATION DESCRIPTION', 'ASSIGNED OPERATOR', 'TARGET OUTPUT', 'OPERATOR EFFICIENCY', 'ACTUAL OUTPUT']])

    except KeyError as e:
        st.error(f"Missing expected column: {e}")

else:
    st.warning("👆 Please upload both the Skill Matrix and Operation Bulletin files.")
