import json
import sys
import os
import copy

# Add the project root to the path so imports work correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from output.doc_struc import process_document, print_hierarchy

def print_full_hierarchy(node, level=0):
    """
    Print the complete hierarchy with all metadata for each node.
    
    Args:
        node: The node to print
        level: The indentation level
    """
    indent = "  " * level
    
    if 'type' in node:
        print(f"{indent}Type: {node['type']}")
        
        # Print all metadata except children
        for key, value in node.items():
            if key == 'children':
                continue
            
            # Skip text for section and table types (often gibberish)
            if key == 'text' and node['type'] in ['section', 'table']:
                continue
                
            # Format box as a single string instead of a dictionary
            if key == 'box' and isinstance(value, dict):
                box_str = f"{value.get('x', 0)} {value.get('y', 0)} {value.get('width', 0)} {value.get('height', 0)}"
                print(f"{indent}  {key}: {box_str}")
            else:
                print(f"{indent}  {key}: {value}")
    
    # Print children recursively
    if 'children' in node:
        print(f"{indent}Children:")
        for child in node['children']:
            print_full_hierarchy(child, level + 1)
            print(f"{indent}{'='*20}")  # Separator between children

def transform_hierarchy_for_output(node):
    """
    Transform the hierarchy for JSON output by:
    1. Removing text fields from sections and tables
    2. Converting box coordinates to space-separated strings
    
    Args:
        node: The node to transform
        
    Returns:
        The transformed node
    """
    # Make a copy to avoid modifying the original
    transformed = copy.deepcopy(node)
    
    # Remove text from sections and tables (usually gibberish)
    if 'type' in transformed and transformed['type'] in ['section', 'table'] and 'text' in transformed:
        del transformed['text']
    
    # Format box as a single string instead of a dictionary
    if 'box' in transformed and isinstance(transformed['box'], dict):
        box = transformed['box']
        transformed['box'] = f"{box.get('x', 0)} {box.get('y', 0)} {box.get('width', 0)} {box.get('height', 0)}"
    
    # Recursively transform children
    if 'children' in transformed:
        transformed['children'] = [transform_hierarchy_for_output(child) for child in transformed['children']]
    
    return transformed

# Load your OCR enriched predictions file
with open("output/ocr_enriched_predictions.json", "r") as f:
    json_data = f.read()

# Process the document
hierarchy = process_document(json_data)

# Print the basic document hierarchy (just type and text)
print("Basic Document Hierarchy:")
print_hierarchy(hierarchy)
print("\n" + "="*50 + "\n")

# Print the full document hierarchy with all metadata
print("Full Document Hierarchy with All Metadata:")
print_full_hierarchy(hierarchy)

# Transform hierarchy for JSON output
transformed_hierarchy = transform_hierarchy_for_output(hierarchy)

# Save the transformed structured output
with open("output/document_hierarchy_test.json", "w") as f:
    json.dump(transformed_hierarchy, indent=2, fp=f)
    print("Hierarchy saved to output/document_hierarchy_test.json") 