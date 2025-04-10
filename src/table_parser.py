import json
import os
import openai
from typing import Dict, List, Any, Tuple
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

def analyze_table_structure(table_data: Dict) -> Dict:
    """
    Analyze the table structure using OpenAI to understand the layout and add context to empty fields.
    """
    # Extract table information
    table_text = table_data.get("text", "")
    fields = table_data.get("fields", [])
    
    # Sort fields by y-coordinate and then x-coordinate to help visualize the table structure
    sorted_fields = sorted(fields, key=lambda f: (f.get("y", 0), f.get("x", 0)))
    
    # Create a prompt for the LLM
    prompt = f"""
    I have a table with the following information:
    
    Table Title: {table_text}
    
    The table has the following fields with their positions (sorted by y-coordinate, then x-coordinate):
    """
    
    # Add field information to the prompt
    for field in sorted_fields:
        field_text = field.get("text", "")
        x = field.get("x", 0)
        y = field.get("y", 0)
        width = field.get("width", 0)
        height = field.get("height", 0)
        field_id = field.get("detection_id", "")
        
        prompt += f"- Field ID: {field_id}, Text: '{field_text}', Position: x={x}, y={y}, width={width}, height={height}\n"
    
    prompt += """
    Based on the positions of these fields, I need to understand the table layout and fill in any empty fields.
    
    The table may have different structures:
    1. A table with a single header row and multiple data rows underneath
    2. A table with header rows and header columns
    3. A table with numbered rows (e.g., State1, State2, etc.)
    
    For tables with a single header row and multiple data rows, each data row should follow the pattern of the header row.
    For example, if there's a table with columns for "State", "Number", and "Expiration Date", and there's an empty field in the "State" column for row 2, the text should be "State1".
    
    For tables with header rows and header columns, each field should be the context of the header row and header column.
        For example, if there's a table with columns for "Type", "State", "Number", and "Expiration Date", and there's an empty field in the "State" column for a "Medical License" row, the text should be "Medical License State".
    For each empty field (where text is empty), determine what text should be in that field based on its position relative to other fields.
    
    Please provide a JSON object where each field ID is a key and the value is the text that should replace the empty field. ONLY return the JSON object, nothing else.
    """
    
    # Call the OpenAI API
    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes table structures and provides appropriate text for empty fields."},
                {"role": "user", "content": prompt}
            ]
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