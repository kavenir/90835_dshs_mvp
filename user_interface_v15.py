import streamlit as st
import json
import openai
from openai import OpenAI
import PyPDF2
import os
import pandas as pd

def setup_openai_api(credentials_path):
    """
    Set up the OpenAI API using credentials from a JSON file.
    Parameters:
        credentials_path (str): Path to the JSON file containing API credentials.
    Returns:
        str: The OpenAI API key.
    """
    with open(credentials_path, 'r') as file:
        credentials = json.load(file)

    openai_api_key = credentials.get('openai_api_key')
    return openai_api_key


def load_patient_data(file_paths):
    """
    Load patient data from multiple JSON files.
    Parameters:
        file_paths (list): List of file paths to the JSON files containing patient data.
    Returns:
        list: A list containing patient data dictionaries for each file.
    """
    patient_data = []
    for path in file_paths:
        with open(path, 'r') as file:
            data = json.load(file)
        patient_data.append(data)
    return patient_data


def load_instruction_text(pdf_path):
    """
    Load text from a PDF document.
    Parameters:
        pdf_path (str): Path to the PDF document.
    Returns:
        str: Text extracted from the PDF.
    """
    pdf_text = ""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            pdf_text += page.extract_text()
    return pdf_text



def get_patient_names_and_ids(patient_data):
    """
    Extract patient names and IDs from patient data.
    Parameters:
        patient_data (list): The patient data containing dictionaries.
    Returns:
        list: A list of tuples containing patient name and ID.
    """
    return [(patient.get('patient_demographics', {}).get('name'), patient.get('patient_id')) for patient in patient_data]



def get_patient_info(selected_patient_data):
    """
    Get additional information about the selected patient.
    Parameters:
        selected_patient_data (list): The list of patient data dictionaries for the selected patient.
    Returns:
        dict: Additional information about the selected patient.
    """
    if selected_patient_data:
        patient_demographics = selected_patient_data.get('patient_demographics', {})
        patient_info = {
            'Age': patient_demographics.get('age'),
            'Gender': patient_demographics.get('gender'),
            'Admission Date': patient_demographics.get('admission_date'),
            'Discharge Date': patient_demographics.get('discharge_date'),
            'Expected Discharge Date': patient_demographics.get('expected_discharge_date')
        }

        return patient_info
    else:
        return {}




def generate_patient_summary(selected_patient_data, additional_prompts='', openai_api_key='',excel_file='log.xlsx'):
    """
    Generates a patient summary using OpenAI's GPT-3.5.
    Parameters:
        selected_patient_data (dict): The patient data for which to generate the summary.
        additional_prompts (str): Additional prompts for the summary.
        openai_api_key (str): The OpenAI API key.
    Returns:
        str: The generated patient summary.
    """

    # client = openai.OpenAI(api_key=openai_api_key)
    # chat_completion = client.chat.completions.create(

    #     messages=[
    #         {
    #             "role": "user",
    #             "content": f"""
    #                           You are a doctor writing a discharge letter for {selected_patient_data.get('patient_demographics', {}).get('name')}. 
    #                           Use patient data from context only. Minimize hallucinations.
    #                           Please do not use bullet point, responses should be in prose.
    #                           {additional_prompts}
    #                           Data: {selected_patient_data}
    #             """,
    #         }
    #     ],
    #     model="gpt-3.5-turbo",
    # )
    # return chat_completion.choices[0].message.content

    # Setup OpenAI client
    client = openai.OpenAI(api_key=openai_api_key)

    # Prepare the prompt
    prompt = f"""
        You are a doctor writing a discharge letter for {selected_patient_data.get('patient_demographics', {}).get('name')}. 
        You are the physician (Dr. Winn AI) in charge of this patient writing the discharge letter
        with the goal of communicating the patient's care plan to the post-hospital care team, the next setting of care, or the caretakers of the patient.
        Please add Dear Post-Hospital Care Team in the beginning and Sincerely DR. Winn AI.
        Use patient data from context only. Minimize hallucinations.
        Please do not use bullet point, responses should be in prose.
        Please add Dear Post-Hospital Care Team in the beginning and Sincerely DR. Winn AI.
        Requirements:
               - Please do not use bullet point, responses should be in prose.
               - Provide a summary of the stay, key issues, interventions, condition at discharge, follow-up plans, and ongoing treatment if relevant.
               - Exclude irrelevant lab data, focusing on first/last labs and any out-of-range values.
               - Reason through whether the patient is safe to discharge, considering any potential errors.
        After generating the discharge letter, review it again to make sure that all the requirements are met, and it is clear to the care teams what they have to do next.  
        Finally, ensure the letter is kept to one page long.
        Data: {selected_patient_data}
    """

    # Generate summary
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-3.5-turbo",
    )
    summary = chat_completion.choices[0].message.content

    # Extract the part of the prompt before "Data:"
    prompt_strip = prompt.split("Data:")[0].strip()
    
    # Create a DataFrame with the prompt and summary
    data = {'Prompt': [prompt_strip], 'Summary': [summary], 'PII': 'with'}
    df = pd.DataFrame(data)

    # If the Excel file doesn't exist, create it with the DataFrame
    if not os.path.exists(excel_file):
        df.to_excel(excel_file, index=False, sheet_name='Logs')
    else:
        # If it exists, load existing data into DataFrame
        existing_df = pd.read_excel(excel_file, sheet_name='Logs')
        # Concatenate existing DataFrame with new data
        updated_df = pd.concat([existing_df, df], ignore_index=True)
        # Write updated DataFrame to Excel file
        updated_df.to_excel(excel_file, index=False, sheet_name='Logs')

    return summary


def generate_patient_summary_without(selected_patient_data, additional_prompts='', openai_api_key='',excel_file='log.xlsx'):
    """
    Generates a patient summary without using PII using OpenAI's GPT-3.5.
    Parameters:
        selected_patient_data (dict): The patient data for which to generate the summary.
        additional_prompts (str): Additional prompts for the summary.
        openai_api_key (str): The OpenAI API key.
    Returns:
        str: The generated patient summary without PII.
    """

    # Exclude 'patient_id' and 'name' fields from the selected patient data
    selected_patient_data_modified = selected_patient_data.copy()
    selected_patient_data_modified.pop('patient_id')
    selected_patient_data_modified['patient_demographics'].pop('name')
    selected_patient_data_modified['patient_demographics'].pop('gender')
    selected_patient_data_modified['patient_demographics'].pop('age')

    # client = openai.OpenAI(api_key=openai_api_key)
    # chat_completion = client.chat.completions.create(

    #     messages=[
    #         {
    #             "role": "user",
    #             "content": f"""
    #                           You are a doctor writing a discharge letter for {selected_patient_data_modified.get('patient_demographics', {}).get('name')}. 
    #                           Use patient data from context only. Minimize hallucinations.
    #                           Please do not use bullet point, responses should be in prose.
    #                           Please do not include "name" and "patient_id".
    #                           {additional_prompts}
    #                           Data: {selected_patient_data_modified}
    #             """,
    #         }
    #     ],
    #     model="gpt-3.5-turbo",
    # )
    # return chat_completion.choices[0].message.content

    # Setup OpenAI client
    client = openai.OpenAI(api_key=openai_api_key)

    # Prepare the prompt
    prompt = f"""
        You are a doctor writing a discharge letter for {selected_patient_data_modified.get('patient_demographics', {}).get('name')}. 
        Use patient data from context only. Minimize hallucinations.
        You are the physician (Dr. Winn AI) in charge of this patient writing the discharge letter 
        with the goal of communicating the patient's care plan to the post-hospital care team, the next setting of care, or the caretakers of the patient.
        Please add Dear Post-Hospital Care Team in the beginning and Sincerely DR. Winn AI.
        Please do not use bullet point, responses should be in prose.
        Please do not include patient name, gender, age, and patient id in the output.
        Requirements:
               - Please do not use bullet point, responses should be in prose.
               - Provide a summary of the stay, key issues, interventions, condition at discharge, follow-up plans, and ongoing treatment if relevant.
               - Exclude irrelevant lab data, focusing on first/last labs and any out-of-range values.
               - Reason through whether the patient is safe to discharge, considering any potential errors.
        After generating the discharge letter, review it again to make sure that all the requirements are met, and it is clear to the care teams what they have to do next.  
        Finally, ensure the letter is kept to one page long.
        Data: {selected_patient_data_modified}
    """

    # Generate summary
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-3.5-turbo",
    )
    summary = chat_completion.choices[0].message.content
    
    # Extract the part of the prompt before "Data:"
    prompt_strip = prompt.split("Data:")[0].strip()
    
    # Create a DataFrame with the prompt and summary
    data = {'Prompt': [prompt_strip], 'Summary': [summary], 'PII': 'without'}
    df = pd.DataFrame(data)

    # If the Excel file doesn't exist, create it with the DataFrame
    if not os.path.exists(excel_file):
        df.to_excel(excel_file, index=False, sheet_name='Logs')
    else:
        # If it exists, load existing data into DataFrame
        existing_df = pd.read_excel(excel_file, sheet_name='Logs')
        # Concatenate existing DataFrame with new data
        updated_df = pd.concat([existing_df, df], ignore_index=True)
        # Write updated DataFrame to Excel file
        updated_df.to_excel(excel_file, index=False, sheet_name='Logs')

    return summary


def main():
    """
    Main function for the discharge summarization application.
    """

    # # Display logo
    # logo_image = 'logo.png' 
    # st.image(logo_image, width=200)
    
    # Display logo and title
    col1, col2 = st.columns([1, 3])  # Adjust the width ratios as needed

    with col1:
        logo_image = 'logo.png' 
        st.image(logo_image, width=150)  # Adjust the width of the logo as needed

    # with col2:
    #     st.title("DOWNMC Health")
    #     st.title("Discharge Summarization System")

    with col2:
        st.markdown("<h1 style='text-align: left; font-size: 30px;'>DOWNMC Health</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: left; font-size: 24px;'>Discharge Summarization System</h2>", unsafe_allow_html=True)



    # st.title("DOWNMC Health")
    # st.title("Discharge Summarization System")

    # Load data
    file_paths = ['data.json', 'data_2.json', 'data_3.json']
    patient_data = load_patient_data(file_paths)

    # OpenAI
    credentials_path = 'credentials.json'
    api_key = setup_openai_api(credentials_path)

    # Load discharge summary introduction
    pdf_path = 'bmc-Transitions-of-Care.pdf'
    pdf_text = load_instruction_text(pdf_path)

    # Extract patient names and IDs
    patient_names_and_ids = get_patient_names_and_ids(patient_data)

    # Dropdown to select patient name and ID
    selected_patient_name_id = st.selectbox("Select Patient:", patient_names_and_ids, format_func=lambda patient: f"{patient[0]} (ID: {patient[1]})")

    # Find selected patient data
    selected_patient_data = next((patient for patient in patient_data if patient.get('patient_demographics', {}).get('name') == selected_patient_name_id[0]), None)

    if selected_patient_data:
        # Display patient information
        st.subheader("Patient Information:")
        patient_info = get_patient_info(selected_patient_data)
        for key, value in patient_info.items():
            st.write(f"- **{key}**: {value}")

        # Check if discharge date is not saved
        if patient_info.get('Discharge Date') is None:
            st.warning("This patient is not safe to discharge!")
        else:
            # Add radio buttons for PII selection
            pii_selection = st.radio("Choose PII option:", ("with PII", "without PII"))

            if pii_selection == "with PII":
                generate_summary_function = generate_patient_summary
            else:
                generate_summary_function = generate_patient_summary_without

            # Generate summary
            additional_prompts = f"Discharge Summary Introduction: {pdf_text}\n"
            if st.button("Generate Summary"):
                summary = generate_summary_function(selected_patient_data, additional_prompts, api_key)
                st.subheader("Generated Summary:")
                st.write(summary)
    else:
        st.error("Patient not found.")

if __name__ == "__main__":
    main()



# cd ~/Desktop/Courses/2023/Semester\ 2/90835\ Smart\ Health/Project/LLM_MVP
# streamlit run user_interface_v15.py