# Required modules
try:
    import streamlit as st
except ModuleNotFoundError:
    print(
        "Streamlit is not installed. Please install it using 'pip install streamlit' and run this script with 'streamlit run script_name.py'")
    exit()

import pandas as pd
import re
import io
import matplotlib.pyplot as plt

st.set_page_config(page_title="CBSE Result Extractor", layout="wide", page_icon="📘")

st.markdown("""
    <div style='background-color:#f0f2f6;padding:10px;border-radius:8px;'>
        <h1 style='text-align: center; color: #2c3e50;'>📘 CBSE Result Extractor</h1>
        <p style='text-align: center; font-size: 16px; color: #555;'>Analyze, visualize and download Class 10 & 12 board results easily</p>
    </div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("📁 Upload CBSE Gazette TXT File", type=["txt", "TXT"])


@st.cache_data
def parse_txt(content):
    pattern = re.compile(
        r"(\d{8})\s+F\s+([A-Z\'\s]+)\s+"  # Roll No & Name
        r"(\d{3})\s+(\d{3})\s+(\d{3})\s+(\d{3})\s+(\d{3})\s+.*?"  # Subject codes
        r"(PASS|COMP|ESSENTIAL REPEAT|FAIL|\S+)\s+"  # Result
        r"(?:(\d{3})\s+[A-Z0-9]+\s+){5}"
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
    if not uploaded_file.name.lower().endswith(".txt"):
        st.error("❌ Please upload a valid .TXT file.")
        st.stop()
    content = uploaded_file.read().decode("utf-8")
    df = parse_txt(content)

    if df.empty:
        st.warning("⚠️ No student records found. Please upload a valid CBSE Gazette TXT file.")
    else:
        st.success("✅ Data extracted and cleaned successfully!")

        st.subheader("🧾 Cleaned Result Data")

        # 🔍 Search Feature
        search = st.text_input("🔍 Search by Roll No or Name").strip().lower()
        if search:
            df = df[df['Roll No'].str.contains(search) | df['Name'].str.lower().str.contains(search)]


        # 🔔 Highlight COMP or low percentage
        def highlight_row(row):
            if row['Result'] == 'ESSENTIAL REPEAT':
                return ['background-color: #ff9999'] * len(row)  # red
            elif row['Result'] == 'COMP':
                return ['background-color: #fff3cd'] * len(row)  # yellow
            elif row['Percentage'] < 33:
                return ['background-color: #ffcccc'] * len(row)  # pink
            return [''] * len(row)


        st.dataframe(df.style.apply(highlight_row, axis=1), use_container_width=True)

        with st.expander("⬇️ Download Full Cleaned Data"):
            buffer_full = io.BytesIO()
            df.to_excel(buffer_full, index=False, engine='openpyxl')
            st.download_button("Download All Students with Total & Percentage", data=buffer_full.getvalue(),
                               file_name="cbse_cleaned_result.xlsx",
                               mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        st.divider()

        # 📊 Data Summary in Tabular Format
        st.markdown("""
        <div style='background-color:#eef2f7; padding:10px; border-radius:10px;'>
        <h4 style='color:#333;'>📊 Result Summary Table</h4>
        </div>
        """, unsafe_allow_html=True)
        result_counts = df['Result'].value_counts().reset_index()
        result_counts.columns = ['Result', 'Count']
        st.dataframe(result_counts, use_container_width=True)

        st.markdown("""
        <div style='background-color:#eef2f7; padding:10px; border-radius:10px;'>
        <h4 style='color:#333;'>📈 Performance Tier Table</h4>
        </div>
        """, unsafe_allow_html=True)
        bins = [0, 33, 45, 60, 75, 100]
        labels = ['Fail (<33%)', 'Pass (33-44%)', 'Second (45-59%)', 'First (60-74%)', 'Distinction (75%+)']
        df['Performance Tier'] = pd.cut(df['Percentage'], bins=bins, labels=labels, right=False)
        tier_counts = df['Performance Tier'].value_counts().sort_index().reset_index()
        tier_counts.columns = ['Tier', 'Count']
        tier_counts = tier_counts[tier_counts['Tier'].isin(['Second (45-59%)', 'First (60-74%)', 'Distinction (75%+)'])]
        st.dataframe(tier_counts, use_container_width=True)

        st.markdown("""
        <div style='background-color:#eef2f7; padding:10px; border-radius:10px;'>
        <h4 style='color:#333;'>📚 Subject-wise Average Marks</h4>
        </div>
        """, unsafe_allow_html=True)
        subject_data = []
        for i in range(1, 6):
            sub_code_col = f"Sub{i} Code"
            sub_mark_col = f"Sub{i} Marks"
            avg_df = df.groupby(sub_code_col)[sub_mark_col].mean().reset_index()
            avg_df.columns = ['Subject Code', 'Average Marks']
            subject_data.append(avg_df)

        avg_all = pd.concat(subject_data).groupby('Subject Code').mean().reset_index().sort_values(by='Average Marks',
                                                                                                   ascending=False)
        st.dataframe(avg_all, use_container_width=True)

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
            st.download_button(f"Download {result_choice} Students", data=res_buffer.getvalue(),
                               file_name=f"{result_choice.lower()}_students.xlsx",
                               mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
