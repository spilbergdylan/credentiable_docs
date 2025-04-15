import json
import os

def extract_tables_from_document_structure(document_structure: dict):
    """
    Extract all tables and their fields from the document structure dictionary.
    
    Args:
        document_structure (dict): The structured document data.
        
    Returns:
        dict: Dictionary containing all tables and their fields
    """
    # Dictionary to store all tables
    all_tables = {}
    
    # Check if the document structure has the expected format
    if 'children' not in document_structure:
        print("Warning: Document structure does not contain 'children' key")
        return all_tables
    
    # Process each section in the document
    for section in document_structure['children']:
        if section.get('type') == 'section' and 'children' in section:
            # Look for tables in section children
            for child in section['children']:
                if child.get('type') == 'table':
                    table_id = child.get('id', f"table_{len(all_tables)}")
                    # Create entry for this table
                    all_tables[table_id] = {
                        'box': child.get('box', ''),
                        'confidence': child.get('confidence', 0),
                        'fields': [],
                        'parent_id': section.get('id', '')  # Store parent section ID for context
                    }
                    
                    # Extract fields from table children
                    if 'children' in child:
                        for field in child['children']:
                            # Add all fields and titles within the table
                            if field.get('type') in ['field', 'title']:
                                all_tables[table_id]['fields'].append({
                                    'id': field.get('id', ''),
                                    'type': field.get('type', ''),
                                    'text': field.get('text', ''),
                                    'box': field.get('box', ''),
                                    'confidence': field.get('confidence', 0)
                                })
    
    return all_tables

if __name__ == "__main__":
    # Example usage for standalone execution
    json_path = "./output/ocr_enriched_predictions_processed.json" # Input file path
    output_path = "./output/extracted_tables.json" # Output file path

    try:
        # Load the document structure from the JSON file
        with open(json_path, 'r') as f:
            document_data = json.load(f)
        
        # Call the function with the loaded data
        tables = extract_tables_from_document_structure(document_data)
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
             os.makedirs(output_dir, exist_ok=True)

        # Save the extracted tables to the output JSON file
        with open(output_path, 'w') as f:
            json.dump(tables, f, indent=2)
        
        print(f"Extracted {len(tables)} tables saved to {output_path}") 

    except FileNotFoundError:
        print(f"Error: Input file not found at {json_path}")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}") 