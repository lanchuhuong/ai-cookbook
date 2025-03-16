import json
import os.path
import re
import zipfile
from datetime import datetime

import openpyxl
import pandas as pd
from adobe.pdfservices.operation.auth.credentials import Credentials
from adobe.pdfservices.operation.exception.exceptions import (
    SdkException,
    ServiceApiException,
    ServiceUsageException,
)
from adobe.pdfservices.operation.execution_context import ExecutionContext
from adobe.pdfservices.operation.io.file_ref import FileRef
from adobe.pdfservices.operation.pdfops.extract_pdf_operation import ExtractPDFOperation
from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_element_type import (
    ExtractElementType,
)
from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_pdf_options import (
    ExtractPDFOptions,
)
from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_renditions_element_type import (
    ExtractRenditionsElementType,
)
from dotenv import load_dotenv

load_dotenv()


def get_dict_xlsx(outputzipextract, xlsx_file):
    """
    Function to read excel output from adobe API
    """
    # Read excel
    df = pd.read_excel(
        os.path.join(outputzipextract, xlsx_file),
        sheet_name="Sheet1",
        engine="openpyxl",
    )

    # Clean df
    df.columns = [re.sub(r"_x([0-9a-fA-F]{4})_", "", col) for col in df.columns]
    df = df.replace({r"_x([0-9a-fA-F]{4})_": ""}, regex=True)

    # Convert df to string
    data_dict = df.to_dict(orient="records")

    return data_dict


def adobeLoader(input_pdf, output_zip_path, client_id, client_secret):
    """
    Function to run adobe API and create output zip file
    """
    # Initial setup, create credentials instance.
    credentials = (
        Credentials.service_principal_credentials_builder()
        .with_client_id(client_id)
        .with_client_secret(client_secret)
        .build()
    )

    # Create an ExecutionContext using credentials and create a new operation instance.
    execution_context = ExecutionContext.create(credentials)
    extract_pdf_operation = ExtractPDFOperation.create_new()

    # Set operation input from a source file.
    source = FileRef.create_from_local_file(input_pdf)
    extract_pdf_operation.set_input(source)

    # Build ExtractPDF options and set them into the operation
    extract_pdf_options: ExtractPDFOptions = (
        ExtractPDFOptions.builder()
        .with_elements_to_extract([ExtractElementType.TEXT, ExtractElementType.TABLES])
        .with_elements_to_extract_renditions(
            [ExtractRenditionsElementType.TABLES, ExtractRenditionsElementType.FIGURES]
        )
        .build()
    )
    extract_pdf_operation.set_options(extract_pdf_options)

    # Execute the operation.
    result: FileRef = extract_pdf_operation.execute(execution_context)

    # Save result to output path
    if os.path.exists(output_zip_path):
        os.remove(output_zip_path)
    result.save_as(output_zip_path)


def extract_text_from_file_adobe(output_zip_path, output_zipextract_folder):
    """
    Function to extract text and table from adobe output zip file
    Read and Process JSON: Opens the structuredData.json file which contains the extracted data in a structured format.
    Data Extraction: Iterates through the elements in the JSON file, collecting text
    directly and processing tables by referring to their file paths in the Excel
    format. Table Processing via get_dict_xlsx: When it encounters a table, it uses
    the file path to call get_dict_xlsx, which reads the Excel file, cleans the
    data, and converts it to a dictionary format. This dictionary is then converted
    into a JSON string and added to the DataFrame.
    """
    json_strings = []
    try:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} unzip file")
        # Open the ZIP file
        with zipfile.ZipFile(output_zip_path, "r") as zip_ref:
            # Extract all the contents of the ZIP file to the current working directory
            zip_ref.extractall(path=output_zipextract_folder)
    except Exception as e:
        print(f"Error processing input: {e}")

    try:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} open json file")
        # Opening JSON file
        with open(
            os.path.join(output_zipextract_folder, "structuredData.json")
        ) as json_file:
            data = json.load(json_file)
    except Exception as e:
        print(f"Error processing output: {e}")

    try:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} extract text")
        dfs = pd.DataFrame()
        page = ""
        # Loop through elements in the document
        for ele in data["elements"]:
            df = pd.DataFrame()

            # Get element page
            if "Page" in ele.keys():
                page = ele["Page"]

            # Append table
            if any(x in ele["Path"] for x in ["Table"]):
                if "filePaths" in ele:
                    if [s for s in ele["filePaths"] if "xlsx" in s]:
                        # Read excel table
                        data_dict = get_dict_xlsx(
                            output_zipextract_folder, ele["filePaths"][0]
                        )
                        json_string = json.dumps(data_dict)
                        json_strings.append(json_string)
                        print(f"the json string is: {json_string}")
                        df = pd.DataFrame({"text": json_string}, index=[0])

            # Append text
            elif "Text" in ele.keys():
                df = pd.DataFrame({"text": ele["Text"]}, index=[0])

            # print(page)
            df["page_number"] = page
            dfs = pd.concat([dfs, df], axis=0)

        dfs = dfs.reset_index(drop=True)

        # Groupby page
        dfs = (
            dfs.groupby("page_number")["text"]
            .apply(lambda x: "\n".join(x))
            .reset_index()
        )
    except Exception as e:
        print("----Error: cannot extract text")
        return None, None
    return dfs, json_strings
