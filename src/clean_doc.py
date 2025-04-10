import json
import os
from typing import Dict, Any, Union

class CleanDoc:
    def __init__(self, input_file: str):
        """Initialize the CleanDoc class with the input file path."""
        self.input_file = input_file
        
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
    
    def clean_document(self) -> Dict[str, Any]:
        """Clean the entire document."""
        with open(self.input_file, 'r') as f:
            doc = json.load(f)
        
        cleaned_doc = {}
        for key, value in doc.items():
            cleaned_doc[key] = self._clean_field(value)
        
        return cleaned_doc
    
    def save_cleaned_document(self, output_file: str):
        """Save the cleaned document to a new file."""
        cleaned_doc = self.clean_document()
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(cleaned_doc, f, indent=2)

if __name__ == "__main__":
    # Example usage
    input_file = "./output/final_doc.json"
    output_file = "./output/cleaned_doc.json"
    
    cleaner = CleanDoc(input_file)
    cleaner.save_cleaned_document(output_file) 