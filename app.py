import os  
import cv2
import base64
import re
import json
import fitz
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from PIL import Image
import google.generativeai as genai  
from database import save_to_database, fetch_cheque_data  # Ensure database.py handles fetch/save

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key="Api key")
model = genai.GenerativeModel("gemini-2.0-flash")

# Streamlit Page Config
st.set_page_config(page_title="CheckMate - Cheque Processing", layout="wide")

# Sidebar Navigation
st.sidebar.title("🔍 Navigation")
page = st.sidebar.radio("Go to", ["🏠 Home", "📄 Cheque Upload", "📈 Analytics"])

# Convert PDF to Images
def convert_pdf_to_images(pdf_path):
    doc = fitz.open(pdf_path)
    image_paths = []
    
    for i, page in enumerate(doc):
        pix = page.get_pixmap()
        img_path = f"cheque_page_{i+1}.jpg"
        pix.save(img_path)
        image_paths.append(img_path)
    
    return image_paths

# Encode Image to Base64 for Gemini API
def encode_image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# Extract Text from Cheque using Gemini API
def extract_text_from_image(image_path):
    base64_image = encode_image_to_base64(image_path)
    
    prompt = """Extract the following details from the cheque image:
    - Account Number
    - Bank Name
    - Payee Name
    - Amount
    Return ONLY a valid JSON object without any extra text. The JSON should have:
            account no: XXXXXXXXXX,
            bank name: "Bank Name",
            payee name: Payee Name,
            amount: 10000.00
    """

    response = model.generate_content([{
        "parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": base64_image}},
            {"text": prompt}
        ]
    }])

    print("🔍 Raw API Response:", response)  # Debugging print

    if response and response.text:
        try:
            json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if json_match:
                extracted_data = json.loads(json_match.group())  # Convert JSON string to dictionary
                print("✅ Extracted JSON Data:", extracted_data)  # Debugging print
                return extracted_data
        except json.JSONDecodeError:
            print("❌ JSON Decode Error!")
            return None

    print("❌ No valid JSON response from Gemini API!")
    return None

# Process Cheques from PDF
def process_cheques_from_pdf(pdf_path):
    images = convert_pdf_to_images(pdf_path)
    extracted_cheques = []  

    for image_path in images:
        st.image(image_path, caption="Extracted Cheque Image", use_container_width=True)

        st.info("🔍 Extracting cheque details...")
        cheque_details = extract_text_from_image(image_path)  # Ensuring cheque_details is always assigned

        if cheque_details:
            extracted_cheques.append(cheque_details)
            st.json(cheque_details)

            # Save extracted cheque details to database
            save_to_database(cheque_details)
            st.success("✅ Cheque details saved to the database!")
        else:
            st.error("❌ Failed to extract cheque details!")

    return extracted_cheques

# **🏠 Home Page**
if page == "🏠 Home":
    st.title("🏠 CheckMate - Cheque Processing System")
    st.divider()

    st.markdown("""
    **Welcome to CheckMate!**  
    This application helps in automating cheque data extraction and processing.  
    - Upload scanned cheque images or PDFs.
    - Extract cheque details automatically using AI.
    - View and analyze processed cheque data.

    **Navigation:**  
    - 📄 **Cheque Upload**: Upload and process cheques.  
    - 📈 **Analytics**: View cheque records and insights.
    """)

# **📄 Cheque Upload Page**
elif page == "📄 Cheque Upload":
    st.title("📄 Upload and Process Cheques")
    st.divider()

    # File Upload Section
    upload_file = st.file_uploader("📂 Upload a PDF or an Image", type=["pdf", "jpg", "jpeg", "png"])

    if upload_file is not None:
        file_extension = upload_file.name.split('.')[-1].lower()
        file_path = f"uploaded_cheque.{file_extension}"

        with open(file_path, "wb") as f:
            f.write(upload_file.getbuffer())

        st.success("✅ File uploaded successfully!")

        if file_extension == "pdf":
            st.info("📄 Processing PDF...")
            cheque_details_list = process_cheques_from_pdf(file_path)

            if cheque_details_list:
                st.success("✅ Cheque details extracted successfully!")
                for i, cheque_details in enumerate(cheque_details_list):
                    st.subheader(f"📜 Cheque {i+1} Details:")
                    st.json(cheque_details)
            else:
                st.error("❌ No cheque details found!")

        else:  # If image
            st.image(file_path, caption="Uploaded Image", use_container_width=True)
            
            st.info("🔍 Extracting cheque details...")
            cheque_details = extract_text_from_image(file_path)  # Ensure cheque_details is defined

            if cheque_details:
                st.json(cheque_details)
                print("✅ Extracted Cheque Data:", cheque_details)  # Debugging print

                # Save extracted cheque details to database
                save_to_database(cheque_details)
                st.success("✅ Cheque details saved to the database!")
            else:
                print("❌ Error: No cheque details extracted!")
                st.error("❌ Failed to extract cheque details!")

# **📈 Analytics Page**
elif page == "📈 Analytics":
    st.title("📈 Cheque Analytics")
    st.divider()
    
    # Fetch cheque data from PostgreSQL
    st.cache_data.clear()
    cheque_data = fetch_cheque_data()

    if cheque_data is not None and not cheque_data.empty:
        st.subheader("📝 Cheque Records")
        st.dataframe(cheque_data, use_container_width=True)

        # Convert 'amount' column to numeric for calculations
        cheque_data["amount"] = pd.to_numeric(cheque_data["amount"], errors="coerce")

        # Display key statistics
        total_cheques = len(cheque_data)
        total_amount = cheque_data["amount"].sum()

        col1, col2 = st.columns(2)
        col1.metric("📄 Total Cheques Processed", total_cheques)
        col2.metric("💰 Total Amount Processed", f"₹{total_amount:,.2f}")

        # CSV Download Button
        csv_data = cheque_data.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Data as CSV", data=csv_data, file_name="cheque_data.csv", mime="text/csv")

# Refresh Data Button
if st.button("🔄 Refresh Data", key="refresh_button"):
    st.session_state["refresh_key"] = st.session_state.get("refresh_key", 0) + 1
    st.rerun()

