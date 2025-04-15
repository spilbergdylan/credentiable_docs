class TableParser:
    def __init__(self, data):
        """
        Initialize the TableParser with JSON data from document processing.
        
        Args:
            data (dict): The JSON data containing tables and fields
        """
        self.data = data
        
    def parse_tables(self):
        """
        Parse all tables in the data and add context to each field.
        
        Returns:
            dict: The updated data with context fields added
        """
        result = self.data.copy()
        
        # Process each table in the data
        for table_id, table_data in result.items():
            fields = table_data.get("fields", [])
            
            # Determine table type and parse accordingly
            if self._is_double_axis_table(fields):
                self._parse_double_axis_table(table_data)
            else:
                self._parse_single_axis_table(table_data)
                
        return result
    
    def _is_double_axis_table(self, fields):
        """
        Determine if a table is a double-axis table based on field structure.
        
        Args:
            fields (list): The list of fields in the table
            
        Returns:
            bool: True if the table is a double-axis table, False otherwise
        """
        # Extract row header candidates (fields on the leftmost side)
        left_fields = []
        for field in fields:
            if field.get("type") == "field" and field.get("text"):
                box = field.get("box", "").split()
                if len(box) >= 4:
                    x = float(box[0])
                    if x < 200:  # Adjust threshold as needed
                        left_fields.append(field)
        
        # If we have multiple different text values on the left side,
        # it's likely a double-axis table with row headers
        unique_left_texts = {f.get("text") for f in left_fields}
        return len(unique_left_texts) > 1
    
    def _parse_double_axis_table(self, table_data):
        """
        Parse a double-axis table where fields are defined by row and column headers.
        
        Args:
            table_data (dict): The table data containing fields
        """
        fields = table_data.get("fields", [])
        
        # Find title for reference
        title_text = "Unknown Table"
        for field in fields:
            if field.get("type") == "title":
                title_text = field.get("text", "").strip()
                break
                
        # If no title found in fields, check in the parent section's children
        if title_text == "Unknown Table" and "parent_id" in table_data:
            parent_section = self.data.get(table_data["parent_id"], {})
            if "children" in parent_section:
                for child in parent_section["children"]:
                    if child.get("type") == "title":
                        title_text = child.get("text", "").strip()
                        break
        
        # Group fields by their rough y-coordinate to identify rows
        rows = {}
        for field in fields:
            if field.get("type") == "field":
                box = field.get("box", "").split()
                if len(box) >= 4:
                    y = float(box[1])
                    # Round to nearest row with higher precision
                    row_y = round(y / 5) * 5
                    if row_y not in rows:
                        rows[row_y] = []
                    rows[row_y].append(field)
        
        # Sort rows by y-coordinate
        sorted_rows = sorted(rows.items(), key=lambda x: x[0])
        
        # First non-empty row is likely header row
        header_row = None
        header_y = None
        for row_y, row_fields in sorted_rows:
            if any(field.get("text") for field in row_fields):
                header_row = row_fields
                header_y = row_y
                break
        
        if not header_row:
            return
        
        # Extract column headers
        column_headers = {}
        for field in header_row:
            if field.get("text"):
                box = field.get("box", "").split()
                if len(box) >= 4:
                    x = float(box[0])
                    column_headers[x] = field.get("text")
        
        # Cache of row headers for each row y-coordinate
        row_headers = {}
        
        # Process each row
        for row_idx, (row_y, row_fields) in enumerate(sorted_rows):
            # Skip header row
            if row_y == header_y:
                continue
            
            # Find row header (leftmost field with text)
            left_field = None
            min_x = float('inf')
            
            for field in row_fields:
                if field.get("text"):
                    box = field.get("box", "").split()
                    if len(box) >= 4:
                        x = float(box[0])
                        if x < min_x and x < 200:  # Use threshold for left side
                            min_x = x
                            row_headers[row_y] = field.get("text")
                            left_field = field
        
        # Fill in missing row headers using nearby rows
        for row_idx, (row_y, row_fields) in enumerate(sorted_rows):
            if row_y == header_y or row_y in row_headers:
                continue
            
            # Find the closest row that has a header
            closest_row_y = None
            min_dist = float('inf')
            for y in row_headers:
                dist = abs(y - row_y)
                if dist < min_dist:
                    min_dist = dist
                    closest_row_y = y
            
            if closest_row_y:
                row_headers[row_y] = row_headers[closest_row_y]
        
        # Now process each field
        for row_y, row_fields in sorted_rows:
            # Skip header row
            if row_y == header_y:
                continue
            
            row_header = row_headers.get(row_y)
            if not row_header:
                continue
                
            # Add context to each empty field in this row
            for field in row_fields:
                if field.get("text") == "":
                    box = field.get("box", "").split()
                    if len(box) >= 4:
                        x = float(box[0])
                        
                        # Find closest column header
                        closest_col_x = min(column_headers.keys(), key=lambda cx: abs(cx - x))
                        column_header = column_headers.get(closest_col_x, "Unknown Column")
                        
                        # Set context without table title
                        field["context"] = f"{row_header} {column_header}"
    
    def _parse_single_axis_table(self, table_data):
        """
        Parse a single-axis table and add context to each field.
        
        Args:
            table_data (dict): The table data to parse
        """
        fields = table_data.get("fields", [])
        
        # Find the title field for context
        title_text = "Unknown Table"
        for field in fields:
            if field.get("type") == "title":
                title_text = field.get("text", "").strip()
                break
        
        # If no title found in fields, check in the parent section's children
        if title_text == "Unknown Table" and "parent_id" in table_data:
            parent_section = self.data.get(table_data["parent_id"], {})
            if "children" in parent_section:
                for child in parent_section["children"]:
                    if child.get("type") == "title":
                        title_text = child.get("text", "").strip()
                        break
        
        # Group fields by approximate y-coordinate to identify rows
        rows = {}
        for field in fields:
            if field.get("type") == "field":
                box = field.get("box", "").split()
                if len(box) >= 4:
                    y = float(box[1])
                    # Use a more flexible row grouping tolerance (± 5 units)
                    grouped = False
                    for row_y in rows.keys():
                        if abs(y - row_y) < 5:  # More flexible tolerance
                            rows[row_y].append(field)
                            grouped = True
                            break
                    if not grouped:
                        rows[y] = [field]
        
        # Sort rows by y-coordinate
        sorted_rows = sorted(rows.items())
        
        # Find header row by looking for the row with the most text fields above data rows
        header_row = None
        header_fields = []
        
        # First, try to find a row with multiple text fields that's near the top
        for row_y, row_fields in sorted_rows:
            # Skip the title row
            title_fields = [f for f in row_fields if f.get("type") == "title"]
            if title_fields:
                continue
                
            text_fields = [f for f in row_fields if f.get("text")]
            if len(text_fields) > 1:  # Look for a row with multiple text fields
                header_row = row_y
                header_fields = row_fields
                break
        
        # If no header found with multiple text fields, try the first non-empty row
        if not header_fields:
            for row_y, row_fields in sorted_rows:
                # Skip the title row
                title_fields = [f for f in row_fields if f.get("type") == "title"]
                if title_fields:
                    continue
                    
                text_fields = [f for f in row_fields if f.get("text")]
                if len(text_fields) > 0:
                    header_row = row_y
                    header_fields = row_fields
                    break
        
        if not header_fields:
            return
        
        # Map column headers to x-coordinates
        column_headers = {}
        for field in header_fields:
            if field.get("text"):
                box = field.get("box", "").split()
                if len(box) >= 4:
                    x = float(box[0])
                    column_headers[x] = field.get("text")
        
        # Process each data row (rows below the header)
        for row_idx, (row_y, row_fields) in enumerate(sorted_rows):
            # Skip header row
            if row_y == header_row:
                continue
                
            # Find row identifier (leftmost field with text)
            row_identifier = None
            min_x = float('inf')
            
            for field in row_fields:
                if field.get("text"):
                    box = field.get("box", "").split()
                    if len(box) >= 4:
                        x = float(box[0])
                        if x < min_x and x < 200:  # Use threshold for left side
                            min_x = x
                            row_identifier = field.get("text")
            
            # Add context to each empty field in this row
            for field in row_fields:
                if field.get("text") == "":
                    box = field.get("box", "").split()
                    if len(box) >= 4:
                        x = float(box[0])
                        
                        # Find closest column header
                        closest_header = None
                        min_dist = float('inf')
                        
                        for col_x, header in column_headers.items():
                            dist = abs(col_x - x)
                            if dist < min_dist:
                                min_dist = dist
                                closest_header = header
                        
                        # Set context without table title
                        if closest_header:
                            if row_identifier:
                                field["context"] = f"{row_identifier} - {closest_header}"
                            else:
                                field["context"] = f"Row {row_idx} - {closest_header}"
                        else:
                            if row_identifier:
                                field["context"] = f"{row_identifier}"
                            else:
                                field["context"] = f"Row {row_idx}"


def process_document_json(json_data):
    """
    Process a document JSON and add context to fields.
    
    Args:
        json_data (dict): The document JSON data
        
    Returns:
        dict: The updated JSON with context fields added
    """
    parser = TableParser(json_data)
    return parser.parse_tables()

def merge_table_results_with_ocr(base_predictions, processed_tables):
    """
    Merge the processed table results with base predictions.
    
    Args:
        base_predictions (dict): The base predictions with document structure
        processed_tables (dict): Dictionary of processed tables
        
    Returns:
        dict: Updated predictions with table fields replaced
    """
    # Create a deep copy of base predictions to avoid modifying the original
    import copy
    updated_predictions = copy.deepcopy(base_predictions)
    
    # Create a mapping of table IDs to their processed data
    table_mapping = {}
    for table_id, table_data in processed_tables.items():
        table_mapping[table_id] = table_data
    
    def update_tables_in_children(children):
        """Recursively update tables in children"""
        for child in children:
            if child.get("type") == "table":
                table_id = child.get("id")
                if table_id in table_mapping:
                    # Get the processed table data
                    processed_table = table_mapping[table_id]
                    
                    # Create a mapping of field IDs to preserve non-context fields
                    field_mapping = {}
                    if "children" in child:
                        field_mapping = {f.get("id"): f for f in child["children"] if f.get("type") == "field"}
                    
                    # Update fields with processed data while preserving original data
                    new_children = []
                    for processed_field in processed_table["fields"]:
                        field_id = processed_field.get("id")
                        if field_id in field_mapping:
                            # Start with original field data
                            updated_field = field_mapping[field_id].copy()
                            # Update with processed field data
                            updated_field.update(processed_field)
                            new_children.append(updated_field)
                        else:
                            new_children.append(processed_field)
                    
                    # Keep any non-field children (like titles)
                    if "children" in child:
                        for original_child in child["children"]:
                            if original_child.get("type") != "field":
                                new_children.append(original_child)
                    
                    # Update the table's children
                    child["children"] = new_children
                    
                    # Add any additional metadata from processed table
                    if "metadata" in processed_table:
                        child["metadata"] = processed_table["metadata"]
            
            # Recursively process children if they exist
            if "children" in child:
                update_tables_in_children(child["children"])
    
    # Start the recursive update from the root
    if "children" in updated_predictions:
        update_tables_in_children(updated_predictions["children"])
    
    return updated_predictions

def process_tables(extracted_tables):
    """
    Process all extracted tables and return the processed results.
    
    Args:
        extracted_tables (dict): Dictionary of extracted tables
        
    Returns:
        dict: Processed tables with added context and structure
    """
    parser = TableParser(extracted_tables)
    return parser.parse_tables()

def update_document_structure_with_processed_tables(doc_structure, processed_tables):
    """
    Update the document structure with processed table results.
    
    Args:
        doc_structure (dict): The original document structure
        processed_tables (dict): The processed table results
        
    Returns:
        dict: Updated document structure
    """
    # Create a deep copy of the document structure
    updated_structure = doc_structure.copy()
    
    # Update each section that contains tables
    for section_id, section in updated_structure.items():
        if "children" in section:
            for child in section["children"]:
                if child.get("type") == "table":
                    table_id = child.get("id")
                    if table_id in processed_tables:
                        # Update the table fields with processed data
                        child["fields"] = processed_tables[table_id].get("fields", [])
                        # Add any additional metadata
                        if "metadata" in processed_tables[table_id]:
                            child["metadata"] = processed_tables[table_id]["metadata"]
    
    return updated_structure


