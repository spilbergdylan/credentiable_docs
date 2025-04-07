import json
from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import Dict, List, Any

class GPTDocumentEnhancer:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it in your .env file.")
        self.client = OpenAI(api_key=api_key)
    
    def enhance_structure(self, structure: Dict, original_predictions: List[Dict]) -> Dict:
        """Enhance the document structure with LLM analysis."""
        # Create a map of all predictions for quick lookup
        predictions_map = {pred['detection_id']: pred for pred in original_predictions}
        
        # Prepare the prompt for the LLM
        prompt = """Analyze this document structure and:
1. Organize the fields into their respective sections
2. Clean up the text in fields, tables, and checkbox elements:
   - Fix OCR errors and typos
   - Remove extra spaces and newlines
   - Standardize formatting
   - Preserve important punctuation
   - Keep empty fields as empty strings
   - Maintain checkbox hierarchies (context -> option -> checkbox)

For each section, include ALL field IDs in the array for their respective sections.
Include ALL table IDs in the array for their respective sections.
Include ALL checkbox_context IDs in the array for their respective sections.

IMPORTANT: 
1. Use the section IDs exactly as they appear in the input structure. Do not add any prefixes or modify the IDs.
2. For tables, include ALL field IDs that belong to that table in the same array as the table ID.
3. Fields that belong to a table should be included in the same array as their parent table.
4. For checkbox contexts, include ALL checkbox_option IDs that belong to that context.
5. For checkbox options, include ALL checkbox IDs that belong to that option.
6. Return both the cleaned text and the original text for each field, table, and checkbox element.

The output should be a JSON object with two parts:
1. "structure": Object where keys are section IDs and values are arrays of field IDs, table IDs, and checkbox_context IDs
2. "cleaned_text": Object mapping detection_ids to their cleaned text values

Example format:
{
    "structure": {
        "d0adf60d-e72b-4ac3-b3a6-770ba7fdaf79": ["field_id_1", "field_id_2", "table_id_1", "checkbox_context_id_1"],
        "96088e19-833e-4ef6-95c6-7f4c653f7c38": ["field_id_5", "field_id_6", "table_id_2", "checkbox_context_id_2"]
    },
    "cleaned_text": {
        "field_id_1": "Last Name",
        "field_id_2": "First Name",
        "table_id_1": "Medical Licensure/Certification",
        "checkbox_context_id_1": "Gender",
        "checkbox_option_id_1": "Male",
        "checkbox_id_1": "☐"
    }
}

Current document structure:
"""
        
        # Add the current structure to the prompt
        prompt += json.dumps(structure, indent=2)
        
        # Get LLM response
        print("\n🔍 Raw LLM Output:")
        llm_response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a document structure analyzer that returns only valid JSON with detection_ids. Always preserve checkbox hierarchies. Use section IDs exactly as they appear in the input. For tables, include all field IDs that belong to that table in the same array. Clean up text by fixing OCR errors and standardizing formatting."},
                {"role": "user", "content": prompt}
            ]
        ).choices[0].message.content
        print(llm_response)
        
        try:
            # Parse the LLM response
            llm_output = json.loads(llm_response)
            return llm_output
            
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            return {"structure": {}, "cleaned_text": {}} 