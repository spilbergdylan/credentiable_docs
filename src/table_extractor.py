import json
import os

def extract_tables_from_document_structure(json_path):
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

if __name__ == "__main__":
    # Example usage
    json_path = "output/document_structure.json"
    tables = extract_tables_from_document_structure(json_path)
    
    # Save the extracted tables to a JSON file
    output_path = "./output/extracted_tables.json"
    with open(output_path, 'w') as f:
        json.dump(tables, f, indent=2)
    
    print(f"Extracted tables saved to {output_path}") 