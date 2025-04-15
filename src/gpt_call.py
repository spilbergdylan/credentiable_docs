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
        prompt = 
        
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