import json
from openai import OpenAI
import argparse
from typing import List, Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv

class DocumentStructurer:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it in your .env file.")
        self.client = OpenAI(api_key=api_key)

    def _is_contained_within(self, element: Dict, container: Dict, threshold: float = 0.8) -> bool:
        """Check if one element is contained within another based on bounding boxes."""
        e_x = float(element['x'])
        e_y = float(element['y'])
        e_w = float(element['width'])
        e_h = float(element['height'])
        
        c_x = float(container['x'])
        c_y = float(container['y'])
        c_w = float(container['width'])
        c_h = float(container['height'])
        
        e_left = e_x - (e_w / 2)
        e_right = e_x + (e_w / 2)
        e_top = e_y - (e_h / 2)
        e_bottom = e_y + (e_h / 2)
        
        c_left = c_x - (c_w / 2)
        c_right = c_x + (c_w / 2)
        c_top = c_y - (c_h / 2)
        c_bottom = c_y + (c_h / 2)
        
        # Special case for tables
        if element.get('class') == 'table':
            # Calculate overlap
            overlap_width = min(e_right, c_right) - max(e_left, c_left)
            overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
            
            if overlap_width <= 0 or overlap_height <= 0:
                return False
                
            element_area = e_w * e_h
            overlap_area = overlap_width * overlap_height
            
            # For tables, require at least 30% vertical overlap with the section
            vertical_overlap_ratio = overlap_height / e_h
            if vertical_overlap_ratio < 0.3:  # Less than 30% vertical overlap
                return False
            
            # Also require significant horizontal overlap (at least 20%)
            horizontal_overlap_ratio = overlap_width / min(e_w, c_w)
            if horizontal_overlap_ratio < 0.2:  # Less than 20% horizontal overlap
                return False
            
            # Check if table is vertically positioned within or very close to the section
            vertical_proximity = 100  # pixels
            is_vertically_close = (
                (e_top >= c_top - vertical_proximity and e_bottom <= c_bottom + vertical_proximity) or  # Table is within or very close to section
                (e_top <= c_bottom + vertical_proximity and e_bottom >= c_top - vertical_proximity)     # Table overlaps with section
            )
            
            return is_vertically_close
        
        # Special case for fields within tables
        if element.get('class') in ['field', 'checkbox', 'checkbox_option', 'checkbox_context'] and container.get('class') == 'table':
            # For fields in tables, use a lower threshold (0.5 or 50% overlap)
            field_threshold = 0.5
            
            # Calculate overlap
            overlap_width = min(e_right, c_right) - max(e_left, c_left)
            overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
            
            if overlap_width <= 0 or overlap_height <= 0:
                return False
                
            element_area = e_w * e_h
            overlap_area = overlap_width * overlap_height
            
            return (overlap_area / element_area) > field_threshold
        
        # Special case for checkbox hierarchy
        if element.get('class') in ['checkbox', 'checkbox_option'] and container.get('class') == 'checkbox_context':
            # For checkboxes within checkbox_context, use a much lower threshold (0.1 or 10% overlap)
            checkbox_threshold = 0.1
            
            # Calculate overlap
            overlap_width = min(e_right, c_right) - max(e_left, c_left)
            overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
            
            if overlap_width <= 0 or overlap_height <= 0:
                return False
                
            element_area = e_w * e_h
            overlap_area = overlap_width * overlap_height
            
            # Also check if checkbox is vertically close to its context
            vertical_proximity = 100  # pixels
            is_vertically_close = (
                abs(e_top - c_bottom) < vertical_proximity or  # Checkbox starts near context bottom
                abs(e_bottom - c_top) < vertical_proximity or  # Checkbox ends near context top
                (e_top >= c_top and e_bottom <= c_bottom)     # Checkbox is fully within context vertically
            )
            
            return is_vertically_close and (overlap_area / element_area) > checkbox_threshold
        
        # Special case for checkbox options within checkbox contexts
        if element.get('class') == 'checkbox_option' and container.get('class') == 'checkbox_context':
            # For checkbox options within checkbox_context, use a lower threshold (0.2 or 20% overlap)
            option_threshold = 0.2
            
            # Calculate overlap
            overlap_width = min(e_right, c_right) - max(e_left, c_left)
            overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
            
            if overlap_width <= 0 or overlap_height <= 0:
                return False
                
            element_area = e_w * e_h
            overlap_area = overlap_width * overlap_height
            
            # Also check if option is vertically close to its context
            vertical_proximity = 120  # pixels
            is_vertically_close = (
                abs(e_top - c_bottom) < vertical_proximity or  # Option starts near context bottom
                abs(e_bottom - c_top) < vertical_proximity or  # Option ends near context top
                (e_top >= c_top and e_bottom <= c_bottom)     # Option is fully within context vertically
            )
            
            return is_vertically_close and (overlap_area / element_area) > option_threshold
        
        # Special case for checkboxes within checkbox options
        if element.get('class') == 'checkbox' and container.get('class') == 'checkbox_option':
            # For checkboxes within checkbox_option, use a very low threshold (0.05 or 5% overlap)
            checkbox_threshold = 0.05
            
            # Calculate overlap
            overlap_width = min(e_right, c_right) - max(e_left, c_left)
            overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
            
            if overlap_width <= 0 or overlap_height <= 0:
                return False
                
            element_area = e_w * e_h
            overlap_area = overlap_width * overlap_height
            
            # Also check if checkbox is vertically close to its option
            vertical_proximity = 80  # pixels
            is_vertically_close = (
                abs(e_top - c_bottom) < vertical_proximity or  # Checkbox starts near option bottom
                abs(e_bottom - c_top) < vertical_proximity or  # Checkbox ends near option top
                (e_top >= c_top and e_bottom <= c_bottom)     # Checkbox is fully within option vertically
            )
            
            return is_vertically_close and (overlap_area / element_area) > checkbox_threshold
        
        # Special case for checkbox contexts within sections
        if element.get('class') == 'checkbox_context' and container.get('class') == 'section':
            # For checkbox contexts within sections, use a lower threshold (0.3 or 30% overlap)
            context_threshold = 0.3
            
            # Calculate overlap
            overlap_width = min(e_right, c_right) - max(e_left, c_left)
            overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
            
            if overlap_width <= 0 or overlap_height <= 0:
                return False
                
            element_area = e_w * e_h
            overlap_area = overlap_width * overlap_height
            
            # Also check if context is vertically close to its section
            vertical_proximity = 150  # pixels
            is_vertically_close = (
                abs(e_top - c_bottom) < vertical_proximity or  # Context starts near section bottom
                abs(e_bottom - c_top) < vertical_proximity or  # Context ends near section top
                (e_top >= c_top and e_bottom <= c_bottom)     # Context is fully within section vertically
            )
            
            return is_vertically_close and (overlap_area / element_area) > context_threshold
        
        # For other elements, use the original overlap calculation
        overlap_width = min(e_right, c_right) - max(e_left, c_left)
        overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
        
        if overlap_width <= 0 or overlap_height <= 0:
            return False
            
        element_area = e_w * e_h
        overlap_area = overlap_width * overlap_height
        
        return (overlap_area / element_area) > threshold

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
                        
                    if self._is_contained_within(other_elem, table_elem):
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
                    'fields': [{
                        'type': 'field',
                        'text': field.get('text', ''),
                        'confidence': field.get('confidence', 0.0),
                        'detection_id': field['detection_id']
                    } for field in table_fields],
                    'checkbox_contexts': [{
                        'type': 'checkbox_context',
                        'text': context.get('text', ''),
                        'confidence': context.get('confidence', 0.0),
                        'detection_id': context['detection_id']
                    } for context in table_checkbox_contexts]
                }
        
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
                        
                    if self._is_contained_within(other_elem, section_elem):
                        if other_elem['class'] == 'field' and other_elem['detection_id'] not in assigned_to_tables:
                            section_fields.append(other_elem)
                        elif other_elem['class'] == 'checkbox_context' and other_elem['detection_id'] not in assigned_to_tables:
                            section_checkbox_contexts.append(other_elem)
                
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
                             if self._is_contained_within(elements_map[table_id], section_elem)},
                    'checkbox_contexts': [{
                        'width': context.get('width', 0.0),
                        'height': context.get('height', 0.0),
                        'x': context.get('x', 0.0),
                        'y': context.get('y', 0.0),
                        'confidence': context.get('confidence', 0.0),
                        'class_id': context.get('class_id', 0),
                        'class': context.get('class', ''),
                        'detection_id': context['detection_id'],
                        'parent_id': context.get('parent_id', ''),
                        'filename': context.get('filename', ''),
                        'text': context.get('text', '')
                    } for context in section_checkbox_contexts]
                }
        
        return sections

    def _enhance_structure_with_llm(self, structure: Dict, original_predictions: List[Dict]) -> Dict:
        """Enhance the document structure with LLM analysis."""
        # Create a map of all predictions for quick lookup
        predictions_map = {pred['detection_id']: pred for pred in original_predictions}
        
        # Prepare the prompt for the LLM
        prompt = """Analyze this document structure and organize the fields into their respective sections.
For each section, include ALL field IDs in the array for their respective sections.
Include ALL table IDs in the array for their respective sections.
Include ALL checkbox_context IDs in the array for their respective sections.

IMPORTANT: 
1. Use the section IDs exactly as they appear in the input structure. Do not add any prefixes or modify the IDs.
2. For tables, include ALL field IDs that belong to that table in the same array as the table ID.
3. Fields that belong to a table should be included in the same array as their parent table.

The output should be a JSON object where:
- Keys are section IDs (use them exactly as they appear in the input)
- Values are arrays of field IDs, table IDs, and checkbox_context IDs that belong to that section

Example format:
{
    "d0adf60d-e72b-4ac3-b3a6-770ba7fdaf79": ["field_id_1", "field_id_2", "table_id_1", "field_id_3", "field_id_4"],
    "96088e19-833e-4ef6-95c6-7f4c653f7c38": ["field_id_5", "field_id_6", "table_id_2", "field_id_7", "field_id_8"]
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
                {"role": "system", "content": "You are a document structure analyzer that returns only valid JSON with detection_ids. Always preserve checkbox hierarchies. Use section IDs exactly as they appear in the input. For tables, include all field IDs that belong to that table in the same array."},
                {"role": "user", "content": prompt}
            ]
        ).choices[0].message.content
        print(llm_response)
        
        try:
            # Parse the LLM response
            llm_structure = json.loads(llm_response)
            
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
                            # Add table with all its metadata
                            tables[element_id] = {
                                'type': 'table',
                                'text': element.get('text', ''),
                                'confidence': element.get('confidence', 0.0),
                                'detection_id': element_id,
                                'fields': []
                            }
                            
                            # Find fields contained within this table
                            for field_id in element_ids:
                                if field_id in predictions_map:
                                    field = predictions_map[field_id]
                                    if field['class'] == 'field' and self._is_contained_within(field, element):
                                        tables[element_id]['fields'].append({
                                            'type': 'field',
                                            'text': field.get('text', ''),
                                            'confidence': field.get('confidence', 0.0),
                                            'detection_id': field['detection_id']
                                        })
                                        fields_in_tables.add(field_id)
                
                # Now process remaining fields and checkbox contexts
                fields = []
                checkbox_contexts = []
                
                for element_id in element_ids:
                    if element_id in predictions_map:
                        element = predictions_map[element_id]
                        
                        if element['class'] == 'field' and element_id not in fields_in_tables:
                            # Add field with all its metadata
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
                                'text': element.get('text', '')
                            })
                        elif element['class'] == 'checkbox_context':
                            # Add checkbox context with all its metadata
                            checkbox_contexts.append({
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
                                'text': element.get('text', '')
                            })
                
                # Create enhanced section entry
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
                    'text': section_data.get('text', ''),
                    'fields': fields,
                    'tables': tables,
                    'checkbox_contexts': checkbox_contexts
                }
            
            return enhanced_structure
            
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            return structure

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
    