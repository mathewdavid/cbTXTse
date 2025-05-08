# Required modules
try:
    import streamlit as st
except ModuleNotFoundError:
    print("Streamlit is not installed. Please install it using 'pip install streamlit' and run this script with 'streamlit run script_name.py'")
    exit()

import pandas as pd
import re
import io

st.set_page_config(page_title="CBSE Result Extractor", layout="wide")

st.title("📊 CBSE Board Result Extractor (10th & 12th)")

uploaded_file = st.file_uploader("📁 Upload CBSE Gazette TXT File", type=["txt", "TXT"])

@st.cache_data
def parse_txt(content):
    pattern = re.compile(
        r"(\d{8})\s+F\s+([A-Z\'\s]+)\s+"  # Roll No & Name
        r"(\d{3})\s+(\d{3})\s+(\d{3})\s+(\d{3})\s+(\d{3})\s+.*?"  # Subject codes
        r"(PASS|COMP|ESSENTIAL REPEAT|FAIL|\S+)\s+"  # Result
        r"(?:(\d{3})\s+[A-Z0-9]+\s+){5}"  # Match marks row
    )

    mark_pattern = re.compile(r"\n\s+((?:\d{3}\s+[A-Z0-9]+\s+){5})")

    matches = list(pattern.finditer(content))
    mark_matches = list(mark_pattern.finditer(content))

    records = []
    for i, match in enumerate(matches):
        try:
            roll = match.group(1)
            name = match.group(2).strip()
            sub_codes = [match.group(j) for j in range(3, 8)]
            result = match.group(8)
            if not result in ['PASS', 'COMP', 'ESSENTIAL REPEAT', 'FAIL']:
                result = 'COMP'

            # Grab marks row from next mark match
            marks_line = mark_matches[i].group(1).strip()
            marks = [int(marks_line.split()[k]) for k in range(0, 10, 2)]

            record = {
                "Roll No": roll,
                "Name": name,
                "Sub1 Code": sub_codes[0], "Sub1 Marks": marks[0],
                "Sub2 Code": sub_codes[1], "Sub2 Marks": marks[1],
                "Sub3 Code": sub_codes[2], "Sub3 Marks": marks[2],
                "Sub4 Code": sub_codes[3], "Sub4 Marks": marks[3],
                "Sub5 Code": sub_codes[4], "Sub5 Marks": marks[4],
                "Total": sum(marks),
                "Percentage": round(sum(marks) / 5, 2),
                "Result": result
            }
            records.append(record)
        except Exception as e:
            print(f"Skipped record due to error: {e}")
            continue

    return pd.DataFrame(records)

if uploaded_file:
    content = uploaded_file.read().decode("utf-8")
    df = parse_txt(content)

    if df.empty:
        st.warning("⚠️ No student records found. Please upload a valid CBSE Gazette TXT file.")
    else:
        st.success("✅ Data extracted and cleaned successfully!")

        st.subheader("🧾 Cleaned Result Data")
        st.dataframe(df, use_container_width=True)

        with st.expander("⬇️ Download Full Cleaned Data"):
            buffer_full = io.BytesIO()
            df.to_excel(buffer_full, index=False, engine='openpyxl')
            st.download_button("Download All Students with Total & Percentage", data=buffer_full.getvalue(), file_name="cbse_cleaned_result.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        st.divider()

        # Subject-wise dropdown and filter
        subject_codes = pd.unique(df[[f"Sub{i} Code" for i in range(1, 6)]].values.ravel())
        subject_choice = st.selectbox("📘 Select Subject Code to View Top Students", options=sorted(subject_codes))

        if subject_choice:
            subject_rows = []
            for i in range(1, 6):
                code_col = f"Sub{i} Code"
                marks_col = f"Sub{i} Marks"
                filtered = df[df[code_col] == subject_choice][["Roll No", "Name", code_col, marks_col]].rename(columns={code_col: "Subject Code", marks_col: "Marks"})
                subject_rows.append(filtered)

            subject_df = pd.concat(subject_rows).sort_values("Marks", ascending=False)
            st.subheader(f"📋 Students List for Subject Code {subject_choice}")
            st.dataframe(subject_df, use_container_width=True)

            sub_buffer = io.BytesIO()
            subject_df.to_excel(sub_buffer, index=False, engine='openpyxl')
            st.download_button(f"Download Subject {subject_choice} Data", data=sub_buffer.getvalue(), file_name=f"subject_{subject_choice}_students.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        st.divider()

        # Result-wise dropdown and filter
        valid_results = ['PASS', 'COMP', 'ESSENTIAL REPEAT']
        result_types = [r for r in df['Result'].dropna().unique() if r in valid_results]
        result_choice = st.selectbox("🎯 Filter Students by Result Status", options=sorted(result_types))

        if result_choice:
            result_df = df[df['Result'] == result_choice]
            st.subheader(f"📄 Students with Result: {result_choice}")
            st.dataframe(result_df, use_container_width=True)

            res_buffer = io.BytesIO()
            result_df.to_excel(res_buffer, index=False, engine='openpyxl')
            st.download_button(f"Download {result_choice} Students", data=res_buffer.getvalue(), file_name=f"{result_choice.lower()}_students.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
