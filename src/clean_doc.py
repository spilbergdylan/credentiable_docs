import json
import os
from typing import Dict, Any, Union

class CleanDoc:
    def __init__(self):
        """Initialize the CleanDoc class."""
        pass # No file needed at init
        
    def _clean_text(self, text_field: Any) -> str:
        """Clean a text field, handling both string and dict formats."""
        if isinstance(text_field, dict):
            return text_field.get('cleaned', '')
        return str(text_field)
        
    def _clean_field(self, field: Union[Dict[str, Any], list]) -> Union[Dict[str, Any], list]:
        """Clean a single field according to the specified rules."""
        if isinstance(field, list):
            return [self._clean_field(item) for item in field]
            
        if not isinstance(field, dict):
            return field
            
        cleaned_field = {}  # Start with empty dict to ensure full cleaning
        
        # Combine spatial information
        if all(key in field for key in ['width', 'height', 'x', 'y']):
            cleaned_field['spatial_info'] = f"{field['width']} {field['height']} {field['x']} {field['y']}"
        
        # Clean text field
        if 'text' in field:
            cleaned_field['text'] = self._clean_text(field['text'])
        
        # Copy allowed fields
        for key in ['confidence', 'filename', 'type', 'fields', 'checkbox_contexts']:
            if key in field:
                if isinstance(field[key], (dict, list)):
                    cleaned_field[key] = self._clean_field(field[key])
                else:
                    cleaned_field[key] = field[key]
        
        # Handle tables specially to preserve their structure
        if 'tables' in field:
            cleaned_field['tables'] = {}
            for table_id, table in field['tables'].items():
                cleaned_table = self._clean_field(table)
                # Clean fields inside tables
                if 'fields' in cleaned_table:
                    cleaned_table['fields'] = [self._clean_field(f) for f in cleaned_table['fields']]
                cleaned_field['tables'][table_id] = cleaned_table
        
        return cleaned_field
    
    def clean_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Clean the entire document dictionary."""
        cleaned_doc = {}
        for key, value in doc.items():
            cleaned_doc[key] = self._clean_field(value)
        
        return cleaned_doc
    
    def save_cleaned_document(self, data_to_save: Dict[str, Any], output_file: str):
        """Save the cleaned document dictionary to a new file."""
        output_dir = os.path.dirname(output_file)
        if output_dir:
             os.makedirs(output_dir, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(data_to_save, f, indent=2)

if __name__ == "__main__":
    # Example usage - needs adjustment if run directly now
    input_file = "./output/final_structured_document.json" # Changed from final_doc.json
    output_file = "./output/cleaned_doc.json"
    
    # Load data first
    try:
        with open(input_file, 'r') as f:
            doc_data = json.load(f)
        
        cleaner = CleanDoc() # Instantiate without file
        cleaned_data = cleaner.clean_document(doc_data) # Clean the loaded data
        cleaner.save_cleaned_document(cleaned_data, output_file) # Save the cleaned data
        print(f"Cleaned document saved to {output_file}")
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file}")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {input_file}") 