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
                if field.get("text", "").strip() == "":
                    # Find the corresponding context in the context_data
                    field_id = field.get("detection_id", "")
                    if field_id in context_data:
                        # Replace the blank text with the table context
                        field["text"] = context_data[field_id]
                    else:
                        # If no specific context found, use a simple fallback
                        field["text"] = "Unknown field"
        
        result[table_id] = processed_table
    
    return result

def main():
    # Load the JSON data
    input_file = "./output/extracted_tables.json"
    output_file = "./output/processed_tables.json"
    
    data = load_json_data(input_file)
    
    # Process the tables
    processed_data = process_tables(data)
    
    # Save the processed data
    save_json_data(processed_data, output_file)
    print(f"Processed data saved to {output_file}")

if __name__ == "__main__":
    main() 