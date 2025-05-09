# Required modules
import streamlit as st
import pandas as pd
import re
import io
import os
import tempfile

st.set_page_config(page_title="CBSE Result Extractor", layout="wide", page_icon="📘")

# Initialize session state variables if they don't exist
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None

# Clear session state button
if st.button("🔄 Clear All Data", key="clear_button"):
    # Create a new session state object with only the keys we want to keep
    for key in list(st.session_state.keys()):
        if key != "clear_button":  # Keep the button state
            del st.session_state[key]
    st.cache_data.clear()
    st.rerun()

st.markdown("""
    <div style='background-color:#f0f2f6;padding:10px;border-radius:8px;'>
        <h1 style='text-align: center; color: #2c3e50;'>📘 CBSE Result Extractor</h1>
        <p style='text-align: center; font-size: 16px; color: #555;'>Analyze, visualize and download Class 10 & 12 board results easily</p>
    </div>
""", unsafe_allow_html=True)

# Alternative approach to file uploading
uploaded_file = st.file_uploader("📁 Upload CBSE Gazette TXT File", accept_multiple_files=False)


@st.cache_data
def parse_txt(content):
    try:
        pattern = re.compile(
            r"(\d{8})\s+F\s+([A-Z\'\s]+)\s+"  # Roll No & Name
            r"(\d{3})\s+(\d{3})\s+(\d{3})\s+(\d{3})\s+(\d{3})\s+.*?"  # Subject codes
            r"(PASS|COMP|ESSENTIAL REPEAT|FAIL|\S+)\s+"  # Result
            r"(?:(\d{3})\s+[A-Z0-9]+\s+){5}"
        )

        mark_pattern = re.compile(r"\n\s+((?:\d{3}\s+[A-Z0-9]+\s+){5})")

        matches = list(pattern.finditer(content))
        mark_matches = list(mark_pattern.finditer(content))

        if not matches or len(matches) == 0:
            return pd.DataFrame()

        records = []
        for i, match in enumerate(matches):
            try:
                if i >= len(mark_matches):
                    continue

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
                st.write(f"Skipped record due to error: {e}")
                continue

        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"Error parsing file: {e}")
        return pd.DataFrame()


# Process the uploaded file
if uploaded_file is not None:
    try:
        # Check if it's a text file
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        if file_extension != '.txt':
            st.error("Please upload a TXT file.")
        else:
            # Save the file to a temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name

            # Read the file content
            with open(tmp_file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Clean up the temporary file
            os.unlink(tmp_file_path)

            # Process the content
            df = parse_txt(content)
            st.session_state.processed_data = df

            if df.empty:
                st.warning("⚠️ No student records found. Please upload a valid CBSE Gazette TXT file.")
            else:
                st.success("✅ Data extracted and cleaned successfully!")
    except Exception as e:
        st.error(f"Error processing file: {e}")
        st.info("Please make sure you're uploading a valid CBSE Gazette TXT file with the correct format.")

# Display and analyze the data if it exists
if st.session_state.processed_data is not None and not st.session_state.processed_data.empty:
    df = st.session_state.processed_data

    st.subheader(f"🧾 Cleaned Result Data ({len(df)})")

    # 🔍 Search Feature
    search = st.text_input("🔍 Search by Roll No or Name").strip().lower()
    if search:
        filtered_df = df[df['Roll No'].str.contains(search) | df['Name'].str.lower().str.contains(search)]
        if filtered_df.empty:
            st.info("No matching records found.")
        else:
            df = filtered_df


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
        st.download_button(
            "Download All Students with Total & Percentage",
            data=buffer_full.getvalue(),
            file_name="cbse_cleaned_result.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

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

    # 📘 Subject Code Filter
    all_subject_codes = pd.unique(df[[f"Sub{i} Code" for i in range(1, 6)]].values.ravel())
    subject_choice = st.selectbox("📘 Select Subject Code to View Top Students", options=sorted(all_subject_codes))

    if subject_choice:
        subject_rows = []
        for i in range(1, 6):
            code_col = f"Sub{i} Code"
            marks_col = f"Sub{i} Marks"
            filtered = df[df[code_col] == subject_choice][["Roll No", "Name", code_col, marks_col]]
            filtered.columns = ["Roll No", "Name", "Subject Code", "Marks"]
            subject_rows.append(filtered)

        subject_df = pd.concat(subject_rows).sort_values("Marks", ascending=False)
        st.subheader(f"📄 Students for Subject Code: {subject_choice} ({len(subject_df)})")
        st.dataframe(subject_df, use_container_width=True)

        sub_buffer = io.BytesIO()
        subject_df.to_excel(sub_buffer, index=False, engine='openpyxl')
        st.download_button(
            f"Download {subject_choice} Subject Data",
            data=sub_buffer.getvalue(),
            file_name=f"subject_{subject_choice}_students.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    st.divider()

    # Result-wise dropdown and filter
    valid_results = ['PASS', 'COMP', 'ESSENTIAL REPEAT']
    result_types = [r for r in df['Result'].dropna().unique() if r in valid_results]
    if result_types:
        result_choice = st.selectbox("🎯 Filter Students by Result Status", options=sorted(result_types))

        if result_choice:
            result_df = df[df['Result'] == result_choice].copy()
            st.subheader(f"📄 Students with Result: {result_choice} ({len(result_df)})")

            if result_choice in ['COMP', 'ESSENTIAL REPEAT'] and 'Performance Tier' in result_df.columns:
                result_df.drop(columns=['Performance Tier'], inplace=True)

            st.dataframe(result_df, use_container_width=True)

            res_buffer = io.BytesIO()
            export_df = result_df.drop(columns=['Performance Tier']) if result_choice in ['COMP', 'ESSENTIAL REPEAT'] and 'Performance Tier' in result_df.columns else result_df
            export_df.to_excel(res_buffer, index=False, engine='openpyxl')
            st.download_button(
                f"Download {result_choice} Students",
                data=res_buffer.getvalue(),
                file_name=f"{result_choice.lower()}_students.xlsx",
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
