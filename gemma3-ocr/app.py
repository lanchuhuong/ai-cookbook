import base64
import io

import ollama
import streamlit as st
from PIL import Image

# Page configuration
st.set_page_config(
    page_title="Gemma-3 OCR",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
    <style>
    .main {
        padding: 1rem;
    }
    .stButton>button {
        width: 100%;
    }
    .stFileUploader {
        padding: 1rem 0;
    }
    .result-box {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #e9ecef;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Header section
st.title("Image Extraction with Gemma-3 🔍")
st.markdown("Extract structured information out of images.")
st.markdown("---")

# Sidebar configuration
with st.sidebar:
    st.header("Image Upload")
    # st.markdown("Upload an image to extract text")

    uploaded_file = st.file_uploader(
        "Choose an image...",
        type=["png", "jpg", "jpeg"],
        help="Supported formats: PNG, JPG, JPEG",
    )

    # Image preview and controls
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_column_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Extract Text", type="primary", use_container_width=True):
                with st.spinner("Processing image..."):
                    try:
                        response = ollama.chat(
                            model="gemma3:4b",
                            messages=[
                                {
                                    "role": "user",
                                    "content": """Analyze the text in the provided image. Extract all readable content
                                            and present it in a structured Markdown format that is clear, concise, 
                                            and well-organized. Ensure proper formatting (e.g., headings, lists, or
                                            code blocks) as necessary to represent the content effectively.""",
                                    "images": [uploaded_file.getvalue()],
                                }
                            ],
                        )
                        st.session_state["ocr_result"] = response["message"]["content"]
                    except Exception as e:
                        st.error(f"Error processing image: {str(e)}")

        with col2:
            if st.button("Clear", type="secondary", use_container_width=True):
                if "ocr_result" in st.session_state:
                    del st.session_state["ocr_result"]
                st.rerun()

# Main content area
if "ocr_result" in st.session_state:
    st.markdown(
        f'<div class="result-box">{st.session_state["ocr_result"]}</div>',
        unsafe_allow_html=True,
    )

# Footer
st.markdown(
    '<p style="text-align: center; color: #666;">Powered by Google Gemma-3 </p>',
    unsafe_allow_html=True,
)
