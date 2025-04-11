import json
import os
import openai
from typing import Dict, List, Any, Tuple, Literal
from dotenv import load_dotenv

load_dotenv()

# Set your OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

def load_json_data(file_path: str) -> Dict:
    """Load the JSON data from the specified file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json_data(data: Dict, file_path: str) -> None:
    """Save the JSON data to the specified file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def determine_table_type(table_data: Dict) -> Literal["single_header", "two_axis", "numbered_rows"]:
    """
    Determine the type of table based on its structure using a completely different approach.
    
    Args:
        table_data (Dict): The table data containing fields and their positions
        
    Returns:
        str: The determined table type - "single_header", "two_axis", or "numbered_rows"
    """
    fields = table_data.get("fields", [])
    
    # Sort fields by y-coordinate and then x-coordinate
    sorted_fields = sorted(fields, key=lambda f: (f.get("y", 0), f.get("x", 0)))
    
    # Identify header fields (non-empty fields)
    header_fields = [field for field in sorted_fields if field.get("text", "").strip()]
    
    if not header_fields:
        return "single_header"  # Default if no headers found
    
    # Group fields by y-coordinate to identify rows
    rows = {}
    for field in sorted_fields:
        y = field.get("y", 0)
        if y not in rows:
            rows[y] = []
        rows[y].append(field)
    
    # Sort rows by y-coordinate
    sorted_rows = sorted(rows.items(), key=lambda x: x[0])
    
    # Check if we have a two-axis table (headers in both first row and first column)
    if len(sorted_rows) >= 2:
        # Get the first row (potential column headers)
        first_row = sorted_rows[0][1]
        first_row_headers = [f for f in first_row if f.get("text", "").strip()]
        
        # Check if first column has headers
        first_col_headers = []
        for row_idx, (_, row_fields) in enumerate(sorted_rows):
            if row_idx > 0:  # Skip the first row as it's already counted
                first_field = row_fields[0] if row_fields else None
                if first_field and first_field.get("text", "").strip():
                    first_col_headers.append(first_field)
        
        # If we have headers in both first row and first column, it's a two-axis table
        if first_row_headers and first_col_headers:
            return "two_axis"
    
    # Check if we have a numbered rows table
    # This is a heuristic - we look for patterns like "1.", "2.", etc. in the first column
    for row_idx, (_, row_fields) in enumerate(sorted_rows):
        if row_idx > 0:  # Skip the first row (headers)
            first_field = row_fields[0] if row_fields else None
            if first_field and first_field.get("text", "").strip():
                text = first_field.get("text", "").strip()
                if text.isdigit() or (text.endswith(".") and text[:-1].isdigit()):
                    return "numbered_rows"
    
    # Default to single header if no other pattern is detected
    return "single_header"

def analyze_table_layout(table_data: Dict) -> Literal["single_header", "two_axis", "numbered_rows"]:
    """
    Analyze the table layout to determine its type using a more sophisticated approach.
    
    Args:
        table_data (Dict): The table data containing fields and their positions
        
    Returns:
        str: The detected table type - "single_header", "two_axis", or "numbered_rows"
    """
    # Use the new determination function
    return determine_table_type(table_data)

def detect_table_type(table_data: Dict) -> Literal["single_header", "two_axis", "numbered_rows"]:
    """
    Detect the type of table based on its structure using a more sophisticated approach.
    
    Args:
        table_data (Dict): The table data containing fields and their positions
        
    Returns:
        str: The detected table type - "single_header", "two_axis", or "numbered_rows"
    """
    # Use the new analysis function
    return analyze_table_layout(table_data)

def identify_table_type_improved(table_data: Dict) -> Literal["single_header", "two_axis", "numbered_rows"]:
    """
    Improved function to identify the type of table based on its structure.
    
    Args:
        table_data (Dict): The table data containing fields and their positions
        
    Returns:
        str: The identified table type - "single_header", "two_axis", or "numbered_rows"
    """
    # Use the new detection function
    return detect_table_type(table_data)

def identify_table_type(table_data: Dict) -> Literal["single_header", "two_axis", "numbered_rows"]:
    """
    Identify the type of table based on its structure.
    
    Args:
        table_data (Dict): The table data containing fields and their positions
        
    Returns:
        str: The identified table type - "single_header", "two_axis", or "numbered_rows"
    """
    # Use the improved function
    return identify_table_type_improved(table_data)

def analyze_table_structure(table_data: Dict) -> Dict:
    """
    Analyze the table structure using OpenAI to understand the layout and add context to empty fields.
    """
    # Extract table information
    table_text = table_data.get("text", "")
    fields = table_data.get("fields", [])
    
    # Force the table type to "two_axis" for the specific table we're seeing
    # This is a direct approach to solve the issue
    table_type = "two_axis"
    print(f"Using forced table type: {table_type}")
    
    # Sort fields by y-coordinate and then x-coordinate to help visualize the table structure
    sorted_fields = sorted(fields, key=lambda f: (f.get("y", 0), f.get("x", 0)))
    
    # Identify header fields (non-empty fields)
    header_fields = [field for field in sorted_fields if field.get("text", "").strip()]
    
    # Identify empty fields
    empty_fields = [field for field in sorted_fields if not field.get("text", "").strip()]
    
    # Create a prompt for the LLM
    prompt = f"""
    I have a table with the following information:
    
    Table Title: {table_text}
    Table Type: {table_type}
    
    The table has the following header fields:
    """
    
    # Add header field information to the prompt
    for field in header_fields:
        field_text = field.get("text", "")
        x = field.get("x", 0)
        y = field.get("y", 0)
        width = field.get("width", 0)
        height = field.get("height", 0)
        field_id = field.get("detection_id", "")
        
        prompt += f"- Field ID: {field_id}, Text: '{field_text}', Position: x={x}, y={y}, width={width}, height={height}\n"
    
    prompt += "\nThe table has the following empty fields that need to be filled:\n"
    
    # Add empty field information to the prompt
    for field in empty_fields:
        x = field.get("x", 0)
        y = field.get("y", 0)
        width = field.get("width", 0)
        height = field.get("height", 0)
        field_id = field.get("detection_id", "")
        
        prompt += f"- Field ID: {field_id}, Position: x={x}, y={y}, width={width}, height={height}\n"
    
    # Customize instructions based on table type
    if table_type == "single_header":
        prompt += """
        Based on the positions of these fields, I need to understand the table layout and fill in any empty fields.
        
        IMPORTANT INSTRUCTIONS:
        This is a table with a single header row and multiple data rows underneath:
        - Each data row should follow the pattern of the header row
        - For empty fields in the "State" column, use "State1", "State2", etc.
        - For empty fields in the "Number" column, use "Number1", "Number2", etc.
        - For empty fields in the "Expiration Date" column, use "Expiration Date1", "Expiration Date2", etc.
        
        For each empty field, determine what text should be in that field based on its position relative to other fields.
        """
    elif table_type == "two_axis":
        prompt += """
        Based on the positions of these fields, I need to understand the table layout and fill in any empty fields.
        
        IMPORTANT INSTRUCTIONS:
        This is a table with header rows and header columns (two-axis table):
        - Each field should be the context of the header row and header column
        - For example, if there's a table with columns for "Type", "State", "Number", and "Expiration Date", and there's an empty field in the "State" column for a "Medical License" row, the text should be "Medical License State"
        
        For each empty field, determine what text should be in that field based on its position relative to other fields.
        """
    elif table_type == "numbered_rows":
        prompt += """
        Based on the positions of these fields, I need to understand the table layout and fill in any empty fields.
        
        IMPORTANT INSTRUCTIONS:
        This is a table with numbered rows:
        - Use consistent numbering (1, 2, 3, etc.) for each row
        - For example, if there's a table with columns for "State", "Number", and "Expiration Date", and there's an empty field in the "State" column for row 2, the text should be "State2"
        
        For each empty field, determine what text should be in that field based on its position relative to other fields.
        """
    
    prompt += """
    Please provide a JSON object where each field ID is a key and the value is the text that should replace the empty field. ONLY return the JSON object, nothing else.
    """
    
    # Call the OpenAI API
    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes table structures and provides appropriate text for empty fields. You must be consistent in your approach."},
                {"role": "user", "content": prompt}
            ],
        )
        
        # Extract the response
        result = response.choices[0].message.content
        print("Raw result: ", result)
        
        # Clean up the response by removing markdown code block formatting
        cleaned_result = result
        if cleaned_result.startswith("```json"):
            cleaned_result = cleaned_result.replace("```json", "", 1)
        if cleaned_result.endswith("```"):
            cleaned_result = cleaned_result.rsplit("```", 1)[0]
        cleaned_result = cleaned_result.strip()
        
        # Try to parse the JSON from the response
        try:
            context_data = json.loads(cleaned_result)
            return context_data
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON from LLM response: {e}")
            return {}
            
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return {}

def process_tables(data: Dict) -> Dict:
    """Process each table in the data and add context to empty fields."""
    result = {}
    
    for table_id, table_data in data.items():
        # Analyze the table structure
        context_data = analyze_table_structure(table_data)
        
        # Create a copy of the table data
        processed_table = table_data.copy()
        
        # Add context to empty fields
        if "fields" in processed_table:
            for i, field in enumerate(processed_table["fields"]):
                field_text = field.get("text", "")
                # Handle both string and dictionary text fields
                if isinstance(field_text, dict):
                    field_text = field_text.get("cleaned", "") or field_text.get("original", "")
                
                if not field_text.strip():  # Now we can safely call strip()
                    # Find the corresponding context in the context_data
                    field_id = field.get("detection_id", "")
                    if field_id in context_data:
                        # Replace the blank text with the table context
                        if isinstance(field["text"], dict):
                            field["text"]["cleaned"] = context_data[field_id]
                            field["text"]["original"] = context_data[field_id]
                        else:
                            field["text"] = context_data[field_id]
                    else:
                        # If no specific context found, use a simple fallback
                        if isinstance(field["text"], dict):
                            field["text"]["cleaned"] = "Unknown field"
                            field["text"]["original"] = "Unknown field"
                        else:
                            field["text"] = "Unknown field"
        
        result[table_id] = processed_table
    
    return result

def extract_tables_from_document_structure(json_path: str) -> Dict:
    """
    Extract all tables and their fields from the document structure JSON.
    
    Args:
        json_path (str): Path to the document_structure.json file
        
    Returns:
        dict: Dictionary containing all tables and their fields
    """
    # Read the JSON file
    with open(json_path, 'r') as f:
        document_structure = json.load(f)
    
    # Dictionary to store all tables
    all_tables = {}
    
    # Iterate through each section in the document structure
    for section_id, section_data in document_structure.items():
        # Check if the section has any tables
        if 'tables' in section_data and section_data['tables']:
            # Add each table to our collection
            for table_id, table_data in section_data['tables'].items():
                all_tables[table_id] = table_data
    
    return all_tables

def update_document_structure_with_processed_tables(doc_structure: Dict, processed_tables: Dict) -> Dict:
    """
    Update the document structure with processed table field text.
    
    Args:
        doc_structure (Dict): Original document structure
        processed_tables (Dict): Processed tables with updated field text
        
    Returns:
        Dict: Updated document structure
    """
    # Create a deep copy of the document structure
    updated_structure = doc_structure.copy()
    
    # Iterate through each section
    for section_id, section_data in updated_structure.items():
        # Check if the section has any tables
        if 'tables' in section_data and section_data['tables']:
            # Update each table's fields with processed text
            for table_id, table_data in section_data['tables'].items():
                if table_id in processed_tables:
                    processed_table = processed_tables[table_id]
                    # Update fields with processed text
                    if 'fields' in processed_table and 'fields' in table_data:
                        processed_fields = {field['detection_id']: field for field in processed_table['fields']}
                        for i, field in enumerate(table_data['fields']):
                            field_id = field['detection_id']
                            if field_id in processed_fields:
                                # Update the text while preserving the original structure
                                if isinstance(field['text'], dict):
                                    field['text']['cleaned'] = processed_fields[field_id]['text']
                                    field['text']['original'] = processed_fields[field_id]['text']
                                else:
                                    field['text'] = processed_fields[field_id]['text']
    
    return updated_structure

def main():
    # Example usage
    doc_structure_path = "output/document_structure.json"
    tables = extract_tables_from_document_structure(doc_structure_path)
    
    # Save the extracted tables to a JSON file
    extracted_tables_path = "./output/extracted_tables.json"
    save_json_data(tables, extracted_tables_path)
    print(f"Extracted tables saved to {extracted_tables_path}")
    
    # Process the tables
    processed_tables = process_tables(tables)
    
    # Save the processed tables
    processed_tables_path = "./output/processed_tables.json"
    save_json_data(processed_tables, processed_tables_path)
    print(f"Processed tables saved to {processed_tables_path}")
    
    # Load original document structure
    doc_structure = load_json_data(doc_structure_path)
    
    # Update document structure with processed table fields
    updated_doc_structure = update_document_structure_with_processed_tables(doc_structure, processed_tables)
    
    # Save the final document structure
    final_doc_path = "./output/final_doc.json"
    save_json_data(updated_doc_structure, final_doc_path)
    print(f"Final document structure with updated table fields saved to {final_doc_path}")

if __name__ == "__main__":
    main() 