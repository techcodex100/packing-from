from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from PyPDF2 import PdfReader
import io, re, os, traceback
from typing import Dict, List, Tuple, Optional

app = FastAPI(title="PDF Form Extractor API", version="1.0.0")

# Enhanced field mapping for PCFC forms with more comprehensive regex patterns
PC_PCFC_MAPPING = [
    # Basic Information
    ("applicant_name",        r"(?:Applicant['\s]*Name|Name of Applicant)[\s:]*\n?([^\n\r]+)"),
    ("applicant_address",     r"(?:Applicant['\s]*Address|Address of Applicant)[\s:]*\n?([^\n\r]+(?:\n[^\n\r]+)*)"),
    ("contact_person",        r"(?:Contact\s+person['\s]*name|Contact Person)[\s:]*\n?([^\n\r]+)"),
    ("mobile",                r"(?:Mobile\s+Number|Phone|Contact)[\s:]*\n?([0-9+\-\s]{8,15})"),
    ("email",                 r"(?:E\s?Mail\s?ID|Email|Email ID)[\s:]*\n?([^\s]+@[^\s]+\.[^\s]+)"),
    ("iec",                   r"(?:Import\s+Export\s+Code|IEC)[\s:]*\n?([A-Za-z0-9]{10})"),
    
    # Financial Information
    ("tenor_days",            r"(?:Tenor\s*\(Number\s+of\s+days\)|Tenor)[\s:]*\n?([0-9]{1,4})"),
    ("po_or_lc_ref",          r"(?:LC/|Purchase\s+Order|PO)\s*reference\s+number[\s:]*\n?([^\n\r]+)"),
    ("po_or_lc_date",         r"(?:Dated|Date)[\s:]*\n?([0-9./-]{8,12})"),
    ("order_value",           r"(?:Order\s+Value|Value)[\s:]*\n?([0-9,.\sA-Z]+)"),
    ("commodity",             r"(?:Commodity|Goods)[\s:]*\n?([^\n\r]+)"),
    ("loan_currency",         r"(?:Loan\s+Currency|Currency)[\s:]*\n?([A-Z]{3})"),
    ("loan_amount_fig",       r"(?:Loan\s+amount\s*\(In\s+figures\)|Amount in Figures)[\s:]*\n?([0-9,.\s]+)"),
    ("loan_amount_words",     r"(?:Loan\s+amount\s*\(In\s+words\)|Amount in Words)[\s:]*\n?([A-Za-z\s\-]+)"),
    
    # Shipping Information
    ("last_shipment_date",    r"(?:Last\s+shipment\s+date|Shipment Date)[\s:]*\n?([0-9./-]{8,12})"),
    ("hs_code",               r"(?:H\s?S\s?Code|HS Code|Harmonized Code)[\s:]*\n?([0-9]+)"),
    ("origin_country",        r"(?:Country\s+of\s+origin\s+of\s+goods|Origin Country)[\s:]*\n?([^\n\r]+)"),
    ("destination_country",   r"(?:Country\s+of\s+destination\s+of\s+goods|Destination Country)[\s:]*\n?([^\n\r]+)"),
    
    # Buyer Information
    ("buyer_name",            r"(?:Buyer['\s]*Name|Name of Buyer)[\s:]*\n?([^\n\r]+)"),
    ("buyer_address",         r"(?:Buyer['\s]*Address|Address of Buyer)[\s:]*\n?([^\n\r]+(?:\n[^\n\r]+)*)"),
    ("credit_account_number", r"(?:Credit\s+the\s+proceeds.*?account\s+number|Account Number)[\s:]*\n?([0-9]+)"),
    
    # Additional fields
    ("pan_number",            r"(?:PAN\s+Number|PAN)[\s:]*\n?([A-Z]{5}[0-9]{4}[A-Z])"),
    ("gst_number",            r"(?:GST\s+Number|GSTIN)[\s:]*\n?([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3})"),
    ("bank_name",             r"(?:Bank\s+Name|Name of Bank)[\s:]*\n?([^\n\r]+)"),
    ("ifsc_code",             r"(?:IFSC\s+Code|IFSC)[\s:]*\n?([A-Z]{4}[0-9]{7})"),
    ("branch_name",           r"(?:Branch\s+Name|Branch)[\s:]*\n?([^\n\r]+)"),
]

# Enhanced field mapping with better validation
FIELD_MAPPING = {
    "untitled1": "Applicant Name",
    "untitled2": "Branch Name", 
    "untitled3": "Branch Address",
    "untitled4": "Contact Person",
    "untitled5": "Mobile Number",
    "untitled6": "Email Address",
    "untitled7": "IEC Number",
    "untitled8": "Beneficiary's Name",
    "untitled9": "Checkbox 1",
    "untitled10": "Checkbox 2",
    "untitled11": "Account Number",
    "untitled12": "Line of Business",
    "untitled13": "Reference Number",
    "untitled14": "Commodity/Service",
    "untitled15": "Amount 1",
    "untitled16": "Remittance Type",
    "untitled17": "Bill Amount (Figures)",
    "untitled18": "Bill Amount (Words)",
    "untitled19": "Bill Currency",
    "untitled20": "Remitter's Name",
    "untitled21": "Remitter's Address",
    "untitled22": "Buyer Name",
    "untitled23": "Buyer Address",
    "untitled24": "Buyer Country",
    "untitled25": "Buyer Account",
    "untitled26": "Currency 1",
    "untitled27": "Debit Account No.",
    "untitled28": "Currency 2",
    "untitled29": "Credit Account No.",
    "untitled30": "Forward Contract No.",
    "untitled31": "Booking Date",
    "untitled32": "Forward Contract Amount",
    "untitled33": "Due Date of Contract",
    "untitled34": "Amount to be Utilized",
    "untitled35": "Exchange Rate",
    "untitled36": "Date",
    "untitled37": "Acknowledgement Number",
    "untitled38": "Reference Number 2",
    "untitled39": "Checkbox 3",
    "untitled40": "Mobile",
    "untitled41": "Email",
    "untitled42": "Address",
    "untitled43": "City",
    "untitled44": "State",
    "untitled45": "Pin Code",
    "untitled46": "Country",
    "untitled47": "IFSC Code",
    "untitled48": "Bank Name",
    "untitled49": "Branch Code",
    "untitled50": "Account Type",
    "untitled51": "Account Number 2",
    "untitled52": "Checkbox 4",
    "untitled53": "Checkbox 5",
    "untitled54": "Checkbox 6",
    "untitled55": "PAN Number",
    "untitled56": "Checkbox 7",
    "untitled57": "Declaration",
    "untitled58": "FCRA No",
    "untitled59": "Other Details"
}

# Field type validation patterns
FIELD_VALIDATION = {
    "Mobile Number": r"^[0-9+\-\s]{8,15}$",
    "Email Address": r"^[^\s]+@[^\s]+\.[^\s]+$",
    "Account Number": r"^[0-9]+$",
    "IEC Number": r"^[A-Za-z0-9]{10}$",
    "PAN Number": r"^[A-Z]{5}[0-9]{4}[A-Z]$",
    "IFSC Code": r"^[A-Z]{4}[0-9]{7}$",
    "Pin Code": r"^[0-9]{6}$",
    "Bill Amount (Figures)": r"^[0-9,.\s]+$",
    "Exchange Rate": r"^[0-9.]+$",
    "Date": r"^[0-9./-]{8,12}$",
    "Booking Date": r"^[0-9./-]{8,12}$",
    "Due Date of Contract": r"^[0-9./-]{8,12}$"
}

def clean_text(text: str) -> str:
    """Clean and normalize extracted text"""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove common OCR artifacts
    text = re.sub(r'[^\w\s@.,\-/():]', '', text)
    
    # Clean up common OCR mistakes
    text = re.sub(r'\b0(?=\d)', 'O', text)  # Replace 0 with O in words
    text = re.sub(r'\b1(?=\d)', 'I', text)  # Replace 1 with I in words
    
    return text.strip()

def validate_and_correct_field(field_name: str, value: str) -> str:
    """Validate field value and correct if needed"""
    if not value or value in ["/Yes", "/Off", "/On"]:
        return value
    
    # Get validation pattern for this field
    pattern = FIELD_VALIDATION.get(field_name)
    if not pattern:
        return value
    
    # Check if value matches expected pattern
    if re.match(pattern, value):
        return value
    
    # Try to correct common issues
    corrected_value = value
    
    # For mobile numbers - extract only digits
    if "Mobile" in field_name:
        digits = re.findall(r'\d', value)
        if len(digits) >= 8:
            corrected_value = ''.join(digits)
    
    # For email - clean up
    elif "Email" in field_name:
        email_match = re.search(r'[^\s]+@[^\s]+\.[^\s]+', value)
        if email_match:
            corrected_value = email_match.group()
    
    # For account numbers - extract only digits
    elif "Account" in field_name or "Number" in field_name:
        digits = re.findall(r'\d', value)
        if digits:
            corrected_value = ''.join(digits)
    
    # For amounts - extract numbers and commas
    elif "Amount" in field_name or "Rate" in field_name:
        amount_match = re.search(r'[0-9,.\s]+', value)
        if amount_match:
            corrected_value = amount_match.group().strip()
    
    # For dates - extract date pattern
    elif "Date" in field_name:
        date_match = re.search(r'[0-9./-]{8,12}', value)
        if date_match:
            corrected_value = date_match.group()
    
    # For PAN - extract PAN pattern
    elif "PAN" in field_name:
        pan_match = re.search(r'[A-Z]{5}[0-9]{4}[A-Z]', value.upper())
        if pan_match:
            corrected_value = pan_match.group()
    
    # For IFSC - extract IFSC pattern
    elif "IFSC" in field_name:
        ifsc_match = re.search(r'[A-Z]{4}[0-9]{7}', value.upper())
        if ifsc_match:
            corrected_value = ifsc_match.group()
    
    return corrected_value

def smart_field_assignment(extracted_data: Dict[str, str]) -> Dict[str, str]:
    """Intelligently assign values to correct fields based on content analysis"""
    corrected_data = {}
    
    # Define field categories
    name_fields = ["Applicant Name", "Beneficiary's Name", "Remitter's Name", "Buyer Name", "Contact Person", "Branch Name"]
    number_fields = ["Mobile Number", "Account Number", "IEC Number", "Reference Number", "Forward Contract No.", "Acknowledgement Number"]
    amount_fields = ["Bill Amount (Figures)", "Forward Contract Amount", "Amount to be Utilized", "Exchange Rate"]
    date_fields = ["Date", "Booking Date", "Due Date of Contract"]
    email_fields = ["Email Address", "Email"]
    address_fields = ["Address", "Remitter's Address", "Buyer Address", "Branch Address"]
    
    # Process each extracted field
    for field_name, value in extracted_data.items():
        if not value or value in ["/Yes", "/Off", "/On"]:
            corrected_data[field_name] = value
            continue
        
        # Validate and correct the value
        corrected_value = validate_and_correct_field(field_name, value)
        corrected_data[field_name] = corrected_value
    
    return corrected_data

def extract_acroform(pdf_bytes: bytes) -> Dict[str, str]:
    """Extract form fields from PDF AcroForm"""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        fields = reader.get_fields() or {}
        cleaned = {}
        
        for k, v in fields.items():
            val = None
            if isinstance(v, dict):
                val = v.get('/V') or v.get('V')
            else:
                val = v
            
            if val is not None:
                cleaned_field_name = FIELD_MAPPING.get(str(k), str(k))
                cleaned_value = clean_text(str(val))
                if cleaned_value:
                    cleaned[cleaned_field_name] = cleaned_value
        
        return cleaned
    except Exception as e:
        return {"error": f"AcroForm extraction failed: {str(e)}"}

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF using PyPDF2"""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error extracting text: {str(e)}"

def extract_pdf_form_fields(pdf_path: str) -> Dict[str, str]:
    """Legacy function for backward compatibility - extracts form fields from PDF file"""
    result = {}
    try:
        reader = PdfReader(pdf_path)
        fields = reader.get_fields()

        if not fields:
            result["message"] = "No form fields found in the PDF."
            return result

        # First pass - extract raw data
        raw_data = {}
        for field_name, field_info in fields.items():
            field_value = field_info.get('/V') or ""
            label = FIELD_MAPPING.get(field_name, field_name)
            cleaned_value = clean_text(str(field_value))
            if cleaned_value:
                raw_data[label] = cleaned_value

        # Second pass - smart field assignment and validation
        result = smart_field_assignment(raw_data)

    except Exception as e:
        result["error"] = str(e)

    return result


@app.post("/extract-json")
async def extract_json(file: UploadFile = File(...)):
    """Legacy endpoint for backward compatibility - extracts form fields from PDF"""
    try:
        # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")
        
        # Create upload directory
        upload_dir = "./uploaded_files"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save uploaded file
        file_location = os.path.join(upload_dir, file.filename)
        with open(file_location, "wb") as f:
            f.write(await file.read())

        # Extract data using legacy method
        extracted_data = extract_pdf_form_fields(file_location)
        
        # Clean up uploaded file
        try:
            os.remove(file_location)
        except:
            pass
            
        return JSONResponse(content=extracted_data)

    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            content={"error": f"Extraction failed: {str(e)}", "traceback": traceback.format_exc()}, 
            status_code=500
        )


@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "message": "PDF Form Extractor API",
        "version": "1.0.0",
        "endpoints": {
            "/extract-json": "Extract form fields from PDF"
        },
        "supported_formats": ["PDF"],
        "max_file_size": "10MB"
    }

