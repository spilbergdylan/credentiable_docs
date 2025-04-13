import sys
import json
import os
from doc_structure import process_document, print_hierarchy

def main():
    # Check if the user provided a file path
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        print("No input file specified. Usage: python run_doc_structure.py path_to_json_file.json")
        return

    # Check if the file exists
    if not os.path.exists(input_file):
        print(f"Error: File {input_file} does not exist.")
        return
    
    try:
        # Load JSON data from file
        with open(input_file, "r") as f:
            json_data = f.read()
        
        # Process the document
        hierarchy = process_document(json_data)
        
        # Print the document hierarchy
        print("\nDocument Hierarchy:")
        print_hierarchy(hierarchy)
        
        # Save the output to a JSON file (same name with _processed suffix)
        output_file = os.path.splitext(input_file)[0] + "_processed.json"
        with open(output_file, "w") as f:
            json.dump(hierarchy, f, indent=2)
        
        print(f"\nProcessed document saved to: {output_file}")
        
    except json.JSONDecodeError:
        print("Error: The file does not contain valid JSON data.")
    except Exception as e:
        print(f"Error processing document: {str(e)}")

if __name__ == "__main__":
    main() 