import streamlit as st
import subprocess
import os

def run_external_script(pdf_file_name, pdf_file_path, folder_name, limit):
    script_path = "process_pdf.py"
    log_file = os.path.join("/tmp", "process_pdf.log")
    with open(log_file, "w") as f:
        subprocess.Popen(["python3", script_path, pdf_file_name, pdf_file_path, folder_name, limit], stdout=f, stderr=f, bufsize=0, universal_newlines=True)

st.header("PDF Scraper")
uploaded = st.file_uploader("PDF", type="pdf")
folder_name = st.text_input("Folder Name")
st.markdown("##### Please ensure the folder name is unique to avoid overwriting existing files.")
st.markdown("##### Hit enter to apply folder name.")
testing = st.checkbox("Testing")
limit = "zero"
if testing:
    limit = st.text_input("Limit: (remember Enter key)")
if uploaded is not None and folder_name:
    button = st.button("Start")
    if button:
        if limit is not None:
            print(f"There was a limit {limit}")
        bytes_data = uploaded.getvalue()
        pdf_file_name = uploaded.name
        pdf_file_path = f"{os.path.join("/tmp")}/{pdf_file_name}"
        with open(pdf_file_path, "wb") as f:
            f.write(bytes_data)
        run_external_script(pdf_file_name, pdf_file_path, folder_name, limit)
        st.header("Started. You can now close the tab.")