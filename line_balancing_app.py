# 📦 Required Libraries
import streamlit as st
import pandas as pd

# 📑 App Title
st.title("🧵 Smart Line Balancing Prototype App")

# 📌 Upload Skill Matrix and Operation Bulletin
skill_file = st.file_uploader("📥 Upload Skill Matrix (Line 5 only) Excel File", type=['xlsx'])
ob_file = st.file_uploader("📥 Upload Operation Bulletin Excel File", type=['xlsx', 'ods'])

if skill_file and ob_file:
    # 📖 Read uploaded files
    skill_df = pd.read_excel(skill_file)
    ob_df = pd.read_excel(ob_file)
    ob_df.columns = ob_df.columns.str.strip()  # removes leading/trailing spaces


    st.subheader("📊 Skill Matrix Preview")
    st.dataframe(skill_df.head())

    st.subheader("📑 Operation Bulletin Preview")
    st.dataframe(ob_df.head())

    # 📌 Preprocess Operation Bulletin
    ob_df = ob_df[['SR. NO', 'OPERATION DESCRIPTION', 'MACHINE SAM', 'MACHINE TYPE']]
    ob_df = ob_df.dropna(subset=['MACHINE TYPE'])

    # 📊 Only present operators
    present_operators = skill_df  # all operators are present per your input

    # 📌 Allocation Logic
    allocation_result = []

    for index, operation in ob_df.iterrows():
        machine_type = operation['MACHINE TYPE']

        # Check if machine_type exists in skill matrix columns
        if machine_type not in present_operators.columns:
            allocation_result.append({
                'Operation': operation['OPERATION DESCRIPTION'],
                'Machine Type': machine_type,
                'SAM': operation['MACHINE SAM'],
                'Allocated Operator': 'No skilled operator available',
                'Skill Level': 'N/A'
            })
            continue

        # Filter operators with skill > 0
        skilled_ops = present_operators[present_operators[machine_type] > 0]

        if not skilled_ops.empty:
            # Pick highest skilled operator
            best_operator = skilled_ops.sort_values(by=machine_type, ascending=False).iloc[0]
            allocation_result.append({
                'Operation': operation['OPERATION DESCRIPTION'],
                'Machine Type': machine_type,
                'SAM': operation['MACHINE SAM'],
                'Allocated Operator': best_operator['Operator Name'],
                'Skill Level': best_operator[machine_type]
            })
            # Remove operator if one-time allocation is needed
            present_operators = present_operators.drop(best_operator.name)
        else:
            allocation_result.append({
                'Operation': operation['OPERATION DESCRIPTION'],
                'Machine Type': machine_type,
                'SAM': operation['MACHINE SAM'],
                'Allocated Operator': 'No skilled operator available',
                'Skill Level': 'N/A'
            })

    allocation_df = pd.DataFrame(allocation_result)

    # 📏 Zig-Zag Position Assignment
    positions = []
    for i in range(len(allocation_df)):
        positions.append(f"L{i+1}" if i % 2 == 0 else f"R{i+1}")
    allocation_df['Position'] = positions

    # 📊 Final Allocation Table
    st.subheader("✅ Final Line Balancing Allocation")
    st.dataframe(allocation_df)

    # 📈 Total SAM & Predicted Pitch Time
    total_sam = allocation_df['SAM'].sum()
    num_operators = allocation_df['Allocated Operator'].nunique() - (allocation_df['Allocated Operator'] == 'No skilled operator available').sum()
    pitch_time = total_sam / num_operators if num_operators > 0 else 0

    st.write(f"🔍 **Total Line SAM:** {total_sam:.2f}")
    st.write(f"📊 **Predicted Pitch Time (Total SAM / Operators Allocated):** {pitch_time:.2f} min")

else:
    st.info("👆 Please upload both the Skill Matrix and Operation Bulletin files to proceed.")

