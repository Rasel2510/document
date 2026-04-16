#!/usr/bin/env python3
"""
JSON to Dart Model Generator (All Fields Nullable)
Usage:
    python json_to_dart.py
    (Then paste your JSON and press Ctrl+D / Cmd+D)
"""

import json
import sys
import re

def to_camel_case(snake_str):
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def to_pascal_case(snake_str):
    return ''.join(x.title() for x in snake_str.split('_'))

def infer_dart_type(value, key_name):
    """Convert JSON value to Dart type string (ignoring nullability here, we add ? later)"""
    if value is None:
        return "dynamic"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "double"
    if isinstance(value, str):
        return "String"
    if isinstance(value, list):
        if value:
            item_type = infer_dart_type(value[0], key_name + "Item")
            return f"List<{item_type}>"
        return "List<dynamic>"
    if isinstance(value, dict):
        return to_pascal_case(key_name)
    return "dynamic"

def generate_class_code(class_name, json_obj, indent=0):
    fields = []
    nested_classes = []
    
    for key, value in json_obj.items():
        field_name = to_camel_case(key)
        if value is None:
            dart_type = "dynamic"
        else:
            dart_type = infer_dart_type(value, key)
        
        # Handle nested objects
        if isinstance(value, dict) and dart_type not in ["String", "int", "double", "bool", "dynamic"]:
            nested_code, _ = generate_class_code(dart_type, value, indent + 1)
            nested_classes.append(nested_code)
            fields.append((field_name, dart_type, key))
        else:
            fields.append((field_name, dart_type, key))
    
    indent_str = "  " * indent
    lines = [f"{indent_str}class {class_name} {{"]
    
    # All fields nullable
    for field_name, dart_type, json_key in fields:
        lines.append(f"{indent_str}  final {dart_type}? {field_name};")
    
    # Constructor with all optional named parameters
    lines.append(f"{indent_str}  {class_name}({{")
    for field_name, dart_type, json_key in fields:
        lines.append(f"{indent_str}    this.{field_name},")
    lines.append(f"{indent_str}  }});")
    
    # fromJson factory - all fields handle null safely
    lines.append(f"{indent_str}  factory {class_name}.fromJson(Map<String, dynamic> json) {{")
    lines.append(f"{indent_str}    return {class_name}(")
    for field_name, dart_type, json_key in fields:
        # For all fields, use conditional access
        if "List<" in dart_type:
            inner_type = re.search(r'List<(.*)>', dart_type).group(1)
            if inner_type[0].isupper():  # List of custom objects
                lines.append(f"{indent_str}      {field_name}: (json['{json_key}'] as List?)?.map((e) => {inner_type}.fromJson(e)).toList(),")
            else:  # List of primitives
                lines.append(f"{indent_str}      {field_name}: json['{json_key}'] != null ? List<{inner_type}>.from(json['{json_key}']) : null,")
        elif dart_type[0].isupper() and dart_type not in ["String", "int", "double", "bool"]:
            # Custom object
            lines.append(f"{indent_str}      {field_name}: json['{json_key}'] != null ? {dart_type}.fromJson(json['{json_key}']) : null,")
        else:
            # Primitive or dynamic
            lines.append(f"{indent_str}      {field_name}: json['{json_key}'],")
    lines.append(f"{indent_str}    );")
    lines.append(f"{indent_str}  }}")
    
    # toJson method - omit nulls for cleaner output, or keep them?
    # Keeping them as null for simplicity
    lines.append(f"{indent_str}  Map<String, dynamic> toJson() {{")
    lines.append(f"{indent_str}    return {{")
    for field_name, dart_type, json_key in fields:
        if "List<" in dart_type:
            inner_type = re.search(r'List<(.*)>', dart_type).group(1)
            if inner_type[0].isupper():
                lines.append(f"{indent_str}      '{json_key}': {field_name}?.map((e) => e.toJson()).toList(),")
            else:
                lines.append(f"{indent_str}      '{json_key}': {field_name},")
        elif dart_type[0].isupper() and dart_type not in ["String", "int", "double", "bool"]:
            lines.append(f"{indent_str}      '{json_key}': {field_name}?.toJson(),")
        else:
            lines.append(f"{indent_str}      '{json_key}': {field_name},")
    lines.append(f"{indent_str}    }};")
    lines.append(f"{indent_str}  }}")
    
    lines.append(f"{indent_str}}}")
    
    class_code = "\n".join(lines)
    all_code = "\n\n".join(nested_classes + [class_code])
    return all_code, fields

def main():
    print("Paste your JSON below and press Ctrl+D (Linux/Mac) or Ctrl+Z (Windows) when done:\n")
    json_str = sys.stdin.read().strip()
    
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        sys.exit(1)
    
    class_name = input("\nEnter the desired class name (e.g., User): ").strip()
    if not class_name:
        class_name = "GeneratedModel"
    else:
        class_name = to_pascal_case(class_name)
    
    dart_code, _ = generate_class_code(class_name, data)
    
    output_file = f"{class_name.lower()}.dart"
    with open(output_file, 'w') as f:
        f.write(dart_code)
    
    print(f"\n✅ Success! Model written to {output_file}")
    print("\n--- Preview ---")
    print(dart_code)

if __name__ == "__main__":
    main()