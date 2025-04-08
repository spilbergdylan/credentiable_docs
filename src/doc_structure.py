import json
import argparse
from typing import List, Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv
from gpt_call import GPTDocumentEnhancer
from spatial_utils import is_contained_within

class DocumentStructurer:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # Initialize the GPT enhancer
        self.gpt_enhancer = GPTDocumentEnhancer()

    def _build_hierarchy(self, predictions: List[Dict]) -> Dict:
        """Build hierarchical structure from predictions."""
        # First, sort all elements by y-coordinate
        sorted_elements = sorted(predictions, key=lambda x: x['y'])
        
        # Create a map of all elements for quick lookup
        elements_map = {elem['detection_id']: elem for elem in predictions}
        
        # Track which elements have been assigned to tables
        assigned_to_tables = set()
        
        # First pass: Process tables and their contained elements
        tables = {}
        for elem in sorted_elements:
            if elem['class'] == 'table':
                table_id = elem['detection_id']
                table_elem = elements_map[table_id]
                
                # Find fields and checkbox contexts contained within this table
                table_fields = []
                table_checkbox_contexts = []
                
                for other_elem in sorted_elements:
                    if other_elem['detection_id'] == table_id:
                        continue
                        
                    if is_contained_within(other_elem, table_elem):
                        if other_elem['class'] == 'field':
                            table_fields.append(other_elem)
                            assigned_to_tables.add(other_elem['detection_id'])
                        elif other_elem['class'] == 'checkbox_context':
                            table_checkbox_contexts.append(other_elem)
                            assigned_to_tables.add(other_elem['detection_id'])
                
                # Create table entry with its fields and checkbox contexts
                tables[table_id] = {
                    'type': 'table',
                    'text': table_elem.get('text', ''),
                    'confidence': table_elem.get('confidence', 0.0),
                    'detection_id': table_id,
                    'width': table_elem.get('width', 0.0),
                    'height': table_elem.get('height', 0.0),
                    'x': table_elem.get('x', 0.0),
                    'y': table_elem.get('y', 0.0),
                    'class_id': table_elem.get('class_id', 0),
                    'class': table_elem.get('class', ''),
                    'parent_id': table_elem.get('parent_id', ''),
                    'filename': table_elem.get('filename', ''),
                    'fields': [{
                        'type': 'field',
                        'text': field.get('text', ''),
                        'confidence': field.get('confidence', 0.0),
                        'detection_id': field['detection_id'],
                        'width': field.get('width', 0.0),
                        'height': field.get('height', 0.0),
                        'x': field.get('x', 0.0),
                        'y': field.get('y', 0.0),
                        'class_id': field.get('class_id', 0),
                        'class': field.get('class', ''),
                        'parent_id': field.get('parent_id', ''),
                        'filename': field.get('filename', '')
                    } for field in table_fields],
                    'checkbox_contexts': []
                }
                
                # Process checkbox contexts within tables
                for context in table_checkbox_contexts:
                    context_id = context['detection_id']
                    context_options = []
                    
                    # Find checkbox options within this context
                    for option_elem in sorted_elements:
                        if option_elem['class'] == 'checkbox_option' and is_contained_within(option_elem, context):
                            option_id = option_elem['detection_id']
                            option_checkboxes = []
                            
                            # Find checkboxes within this option
                            for checkbox_elem in sorted_elements:
                                if checkbox_elem['class'] == 'checkbox' and is_contained_within(checkbox_elem, option_elem):
                                    option_checkboxes.append({
                                        'type': 'checkbox',
                                        'text': checkbox_elem.get('text', ''),
                                        'confidence': checkbox_elem.get('confidence', 0.0),
                                        'detection_id': checkbox_elem['detection_id']
                                    })
                            
                            context_options.append({
                                'type': 'checkbox_option',
                                'text': option_elem.get('text', ''),
                                'confidence': option_elem.get('confidence', 0.0),
                                'detection_id': option_id,
                                'checkboxes': option_checkboxes
                            })
                    
                    tables[table_id]['checkbox_contexts'].append({
                        'type': 'checkbox_context',
                        'text': context.get('text', ''),
                        'confidence': context.get('confidence', 0.0),
                        'detection_id': context_id,
                        'width': context.get('width', 0.0),
                        'height': context.get('height', 0.0),
                        'x': context.get('x', 0.0),
                        'y': context.get('y', 0.0),
                        'class_id': context.get('class_id', 0),
                        'class': context.get('class', ''),
                        'parent_id': context.get('parent_id', ''),
                        'filename': context.get('filename', ''),
                        'options': context_options
                    })
        
        # Second pass: Process sections and their contained elements
        sections = {}
        for elem in sorted_elements:
            if elem['class'] == 'section':
                section_id = elem['detection_id']
                section_elem = elements_map[section_id]
                
                # Find fields and checkbox contexts contained within this section
                # but not already assigned to tables
                section_fields = []
                section_checkbox_contexts = []
                
                for other_elem in sorted_elements:
                    if other_elem['detection_id'] == section_id:
                        continue
                        
                    if is_contained_within(other_elem, section_elem):
                        if other_elem['class'] == 'field' and other_elem['detection_id'] not in assigned_to_tables:
                            section_fields.append(other_elem)
                        elif other_elem['class'] == 'checkbox_context' and other_elem['detection_id'] not in assigned_to_tables:
                            section_checkbox_contexts.append(other_elem)
                
                # Process checkbox contexts within sections
                processed_checkbox_contexts = []
                for context in section_checkbox_contexts:
                    context_id = context['detection_id']
                    context_options = []
                    
                    # Find checkbox options within this context
                    for option_elem in sorted_elements:
                        if option_elem['class'] == 'checkbox_option' and is_contained_within(option_elem, context):
                            option_id = option_elem['detection_id']
                            option_checkboxes = []
                            
                            # Find checkboxes within this option
                            for checkbox_elem in sorted_elements:
                                if checkbox_elem['class'] == 'checkbox' and is_contained_within(checkbox_elem, option_elem):
                                    option_checkboxes.append({
                                        'type': 'checkbox',
                                        'text': checkbox_elem.get('text', ''),
                                        'confidence': checkbox_elem.get('confidence', 0.0),
                                        'detection_id': checkbox_elem['detection_id']
                                    })
                            
                            context_options.append({
                                'type': 'checkbox_option',
                                'text': option_elem.get('text', ''),
                                'confidence': option_elem.get('confidence', 0.0),
                                'detection_id': option_id,
                                'checkboxes': option_checkboxes
                            })
                    
                    processed_checkbox_contexts.append({
                        'type': 'checkbox_context',
                        'text': context.get('text', ''),
                        'confidence': context.get('confidence', 0.0),
                        'detection_id': context_id,
                        'width': context.get('width', 0.0),
                        'height': context.get('height', 0.0),
                        'x': context.get('x', 0.0),
                        'y': context.get('y', 0.0),
                        'class_id': context.get('class_id', 0),
                        'class': context.get('class', ''),
                        'parent_id': context.get('parent_id', ''),
                        'filename': context.get('filename', ''),
                        'options': context_options
                    })
                
                # Create section entry with its fields, tables, and checkbox contexts
                sections[section_id] = {
                    'width': section_elem.get('width', 0.0),
                    'height': section_elem.get('height', 0.0),
                    'x': section_elem.get('x', 0.0),
                    'y': section_elem.get('y', 0.0),
                    'confidence': section_elem.get('confidence', 0.0),
                    'class_id': section_elem.get('class_id', 0),
                    'class': section_elem.get('class', ''),
                    'detection_id': section_id,
                    'parent_id': section_elem.get('parent_id', ''),
                    'filename': section_elem.get('filename', ''),
                    'text': section_elem.get('text', ''),
                    'fields': [{
                        'width': field.get('width', 0.0),
                        'height': field.get('height', 0.0),
                        'x': field.get('x', 0.0),
                        'y': field.get('y', 0.0),
                        'confidence': field.get('confidence', 0.0),
                        'class_id': field.get('class_id', 0),
                        'class': field.get('class', ''),
                        'detection_id': field['detection_id'],
                        'parent_id': field.get('parent_id', ''),
                        'filename': field.get('filename', ''),
                        'text': field.get('text', '')
                    } for field in section_fields],
                    'tables': {table_id: table_data for table_id, table_data in tables.items() 
                             if is_contained_within(elements_map[table_id], section_elem)},
                    'checkbox_contexts': processed_checkbox_contexts
                }
        
        return sections

    def _enhance_structure_with_llm(self, structure: Dict, original_predictions: List[Dict]) -> Dict:
        """Enhance the document structure with LLM analysis."""
        # Create a map of all predictions for quick lookup
        predictions_map = {pred['detection_id']: pred for pred in original_predictions}
        
        # Get LLM response from the GPT enhancer
        llm_output = self.gpt_enhancer.enhance_structure(structure, original_predictions)
        llm_structure = llm_output['structure']
        cleaned_text = llm_output.get('cleaned_text', {})
        
        # Create enhanced structure
        enhanced_structure = {}
        
        # Process each section
        for section_id, element_ids in llm_structure.items():
            if section_id not in structure:
                continue
                
            section_data = structure[section_id]
            
            # Track which fields have been assigned to tables
            fields_in_tables = set()
            
            # First, process tables and their fields
            tables = {}
            for element_id in element_ids:
                if element_id in predictions_map:
                    element = predictions_map[element_id]
                    if element['class'] == 'table':
                        # Add table with all its metadata and cleaned text
                        tables[element_id] = {
                            'type': 'table',
                            'text': cleaned_text.get(element_id, element.get('text', '')),
                            'confidence': element.get('confidence', 0.0),
                            'detection_id': element_id,
                            'width': element.get('width', 0.0),
                            'height': element.get('height', 0.0),
                            'x': element.get('x', 0.0),
                            'y': element.get('y', 0.0),
                            'class_id': element.get('class_id', 0),
                            'class': element.get('class', ''),
                            'parent_id': element.get('parent_id', ''),
                            'filename': element.get('filename', ''),
                            'fields': [],
                            'checkbox_contexts': []
                        }
                        
                        # Find fields and checkbox contexts contained within this table
                        for field_id in element_ids:
                            if field_id in predictions_map:
                                field = predictions_map[field_id]
                                if field['class'] == 'field' and is_contained_within(field, element):
                                    tables[element_id]['fields'].append({
                                        'type': 'field',
                                        'text': cleaned_text.get(field_id, field.get('text', '')),
                                        'confidence': field.get('confidence', 0.0),
                                        'detection_id': field['detection_id'],
                                        'width': field.get('width', 0.0),
                                        'height': field.get('height', 0.0),
                                        'x': field.get('x', 0.0),
                                        'y': field.get('y', 0.0),
                                        'class_id': field.get('class_id', 0),
                                        'class': field.get('class', ''),
                                        'parent_id': field.get('parent_id', ''),
                                        'filename': field.get('filename', '')
                                    })
                                    fields_in_tables.add(field_id)
                                elif field['class'] == 'checkbox_context' and is_contained_within(field, element):
                                    # Process checkbox context within table
                                    context_options = []
                                    for option_id in element_ids:
                                        if option_id in predictions_map:
                                            option = predictions_map[option_id]
                                            if option['class'] == 'checkbox_option' and is_contained_within(option, field):
                                                option_checkboxes = []
                                                for checkbox_id in element_ids:
                                                    if checkbox_id in predictions_map:
                                                        checkbox = predictions_map[checkbox_id]
                                                        if checkbox['class'] == 'checkbox' and is_contained_within(checkbox, option):
                                                            option_checkboxes.append({
                                                                'type': 'checkbox',
                                                                'text': cleaned_text.get(checkbox_id, checkbox.get('text', '')),
                                                                'confidence': checkbox.get('confidence', 0.0),
                                                                'detection_id': checkbox_id
                                                            })
                                                context_options.append({
                                                    'type': 'checkbox_option',
                                                    'text': cleaned_text.get(option_id, option.get('text', '')),
                                                    'confidence': option.get('confidence', 0.0),
                                                    'detection_id': option_id,
                                                    'checkboxes': option_checkboxes
                                                })
                                    tables[element_id]['checkbox_contexts'].append({
                                        'type': 'checkbox_context',
                                        'text': cleaned_text.get(field_id, field.get('text', '')),
                                        'confidence': field.get('confidence', 0.0),
                                        'detection_id': field_id,
                                        'width': field.get('width', 0.0),
                                        'height': field.get('height', 0.0),
                                        'x': field.get('x', 0.0),
                                        'y': field.get('y', 0.0),
                                        'class_id': field.get('class_id', 0),
                                        'class': field.get('class', ''),
                                        'parent_id': field.get('parent_id', ''),
                                        'filename': field.get('filename', ''),
                                        'options': context_options
                                    })
            
            # Now process remaining fields and checkbox contexts
            fields = []
            checkbox_contexts = []
            
            # First, add fields that are explicitly assigned to this section by the LLM
            for element_id in element_ids:
                if element_id in predictions_map:
                    element = predictions_map[element_id]
                    if element['class'] == 'field' and element_id not in fields_in_tables:
                        # Add field with all its metadata and cleaned text
                        fields.append({
                            'width': element.get('width', 0.0),
                            'height': element.get('height', 0.0),
                            'x': element.get('x', 0.0),
                            'y': element.get('y', 0.0),
                            'confidence': element.get('confidence', 0.0),
                            'class_id': element.get('class_id', 0),
                            'class': element.get('class', ''),
                            'detection_id': element_id,
                            'parent_id': element.get('parent_id', ''),
                            'filename': element.get('filename', ''),
                            'text': cleaned_text.get(element_id, element.get('text', ''))
                        })
                    elif element['class'] == 'checkbox_context':
                        # Process checkbox context with its options and checkboxes
                        context_options = []
                        for option_id in element_ids:
                            if option_id in predictions_map:
                                option = predictions_map[option_id]
                                if option['class'] == 'checkbox_option' and is_contained_within(option, element):
                                    option_checkboxes = []
                                    for checkbox_id in element_ids:
                                        if checkbox_id in predictions_map:
                                            checkbox = predictions_map[checkbox_id]
                                            if checkbox['class'] == 'checkbox' and is_contained_within(checkbox, option):
                                                option_checkboxes.append({
                                                    'type': 'checkbox',
                                                    'text': cleaned_text.get(checkbox_id, checkbox.get('text', '')),
                                                    'confidence': checkbox.get('confidence', 0.0),
                                                    'detection_id': checkbox_id
                                                })
                                    context_options.append({
                                        'type': 'checkbox_option',
                                        'text': cleaned_text.get(option_id, option.get('text', '')),
                                        'confidence': option.get('confidence', 0.0),
                                        'detection_id': option_id,
                                        'checkboxes': option_checkboxes
                                    })
                        checkbox_contexts.append({
                            'type': 'checkbox_context',
                            'text': cleaned_text.get(element_id, element.get('text', '')),
                            'confidence': element.get('confidence', 0.0),
                            'detection_id': element_id,
                            'width': element.get('width', 0.0),
                            'height': element.get('height', 0.0),
                            'x': element.get('x', 0.0),
                            'y': element.get('y', 0.0),
                            'class_id': element.get('class_id', 0),
                            'class': element.get('class', ''),
                            'parent_id': element.get('parent_id', ''),
                            'filename': element.get('filename', ''),
                            'options': context_options
                        })
            
            # Then, add any fields that are spatially contained within this section but not yet assigned
            section_elem = predictions_map[section_id]
            for pred in original_predictions:
                if (pred['class'] == 'field' and 
                    pred['detection_id'] not in fields_in_tables and 
                    pred['detection_id'] not in [f['detection_id'] for f in fields] and
                    is_contained_within(pred, section_elem)):
                    fields.append({
                        'width': pred.get('width', 0.0),
                        'height': pred.get('height', 0.0),
                        'x': pred.get('x', 0.0),
                        'y': pred.get('y', 0.0),
                        'confidence': pred.get('confidence', 0.0),
                        'class_id': pred.get('class_id', 0),
                        'class': pred.get('class', ''),
                        'detection_id': pred['detection_id'],
                        'parent_id': pred.get('parent_id', ''),
                        'filename': pred.get('filename', ''),
                        'text': cleaned_text.get(pred['detection_id'], pred.get('text', ''))
                    })
            
            # Create enhanced section entry with cleaned text
            enhanced_structure[section_id] = {
                'width': section_data.get('width', 0.0),
                'height': section_data.get('height', 0.0),
                'x': section_data.get('x', 0.0),
                'y': section_data.get('y', 0.0),
                'confidence': section_data.get('confidence', 0.0),
                'class_id': section_data.get('class_id', 0),
                'class': section_data.get('class', ''),
                'detection_id': section_id,
                'parent_id': section_data.get('parent_id', ''),
                'filename': section_data.get('filename', ''),
                'text': cleaned_text.get(section_id, section_data.get('text', '')),
                'fields': fields,
                'tables': tables,
                'checkbox_contexts': checkbox_contexts
            }
        
        return enhanced_structure

    def process(self, predictions_file: str, output_file: str):
        """Process the OCR predictions and create a structured document."""
        # Load predictions
        with open(predictions_file, 'r', encoding='utf-8') as f:
            predictions = json.load(f)
        
        # Build initial hierarchy
        structure = self._build_hierarchy(predictions)
        
        # Enhance with LLM, passing original predictions
        enhanced_structure = self._enhance_structure_with_llm(structure, predictions)
        
        # Save results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_structure, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Document structure saved to {output_file}")


def main():
    # Create output directory if it doesn't exist
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)

    # Default paths relative to script location
    default_input = output_dir / "ocr_enriched_predictions.json"
    default_output = output_dir / "document_structure.json"

    parser = argparse.ArgumentParser(description='Process document structure from OCR predictions')
    parser.add_argument('--input', default=str(default_input),
                      help='Path to OCR enriched predictions JSON')
    parser.add_argument('--output', default=str(default_output),
                      help='Path to save the structured output')
    
    args = parser.parse_args()
    
    try:
        structurer = DocumentStructurer()
        structurer.process(args.input, args.output)
    except ValueError as e:
        print(f"Error: {e}")
        print("\nPlease set your OpenAI API key using:")
        print("export OPENAI_API_KEY=your_api_key_here")
        exit(1)


if __name__ == "__main__":
    main()
    