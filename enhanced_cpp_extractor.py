import json
import sys
from collections import defaultdict
from typing import Dict, List, Any, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass  # Python < 3.7 doesn't have reconfigure

CPP_KEYWORDS = {
    "if", "else", "switch", "case", "default", "break", "continue",
    "for", "while", "do", "goto", "return",
    "void", "bool", "char", "int", "float", "double", "long", "short",
    "signed", "unsigned", "auto", "const", "static", "extern", "register",
    "volatile", "mutable", "constexpr", "decltype", "typedef",
    "class", "struct", "union", "enum", "namespace", "template",
    "typename", "public", "private", "protected", "virtual", "friend",
    "this", "operator", "new", "delete", "explicit", "inline",
    "sizeof", "alignof", "nullptr",
    "try", "catch", "throw", "noexcept",
    "constexpr", "static_assert", "thread_local", "override", "final",
    "nullptr", "alignas", "decltype", "noexcept"
}

OPERATOR_MAP = {
    "+": "addition",
    "-": "subtraction",
    "*": "multiplication",
    "/": "division",
    "%": "modulus",
    "++": "increment",
    "--": "decrement",
    "<": "less than",
    ">": "greater than",
    "<=": "less than or equal to",
    ">=": "greater than or equal to",
    "==": "equal to",
    "!=": "not equal to",
    "&&": "logical and",
    "||": "logical or",
    "!": "logical not",
    "&": "bitwise and",
    "|": "bitwise or",
    "^": "bitwise xor",
    "~": "bitwise not",
    "<<": "left shift",
    ">>": "right shift",
    "=": "assignment",
    "+=": "add and assign",
    "-=": "subtract and assign",
    "*=": "multiply and assign",
    "/=": "divide and assign",
    "%=": "modulus and assign",
    "&=": "bitwise and assign",
    "|=": "bitwise or assign",
    "^=": "bitwise xor assign",
    "<<=": "left shift and assign",
    ">>=": "right shift and assign"
}

COMPARISON_OPS = {
    "<", ">", "<=", ">=", "==", "!="
}

LOGICAL_OPS = {
    "&&", "||", "!"
}


IR = {}
GLOBAL_METADATA = {
    "keywords_used": set(),
    "operators_used": set(),
    "includes": [],
    "namespaces": [],
    "classes": [],
    "functions": [],
    "global_variables": []
}

current_function = None
current_target = None
current_scope = "global"

def normalize_type(type_info):
    """Extract and normalize C++ type information"""
    if not type_info:
        return {"base_type": "unknown", "qualifiers": [], "is_pointer": False, "is_reference": False}
    
    if isinstance(type_info, str):
        qual_type = type_info
    else:
        qual_type = type_info.get("qualType", "unknown")
    
    result = {
        "base_type": "unknown",
        "qualifiers": [],
        "is_pointer": False,
        "is_reference": False,
        "is_const": False,
        "raw_type": qual_type
    }
    
    if "const" in qual_type:
        result["qualifiers"].append("const")
        result["is_const"] = True
        GLOBAL_METADATA["keywords_used"].add("const")
    
    if "static" in qual_type:
        result["qualifiers"].append("static")
        GLOBAL_METADATA["keywords_used"].add("static")
    
    if "volatile" in qual_type:
        result["qualifiers"].append("volatile")
        GLOBAL_METADATA["keywords_used"].add("volatile")
    
    if "*" in qual_type:
        result["is_pointer"] = True
    
    if "&" in qual_type:
        result["is_reference"] = True
    
    clean_type = qual_type.replace("const", "").replace("static", "").replace("*", "").replace("&", "").strip()
    
    if "int" in clean_type or clean_type in ["short", "long", "unsigned", "signed"]:
        result["base_type"] = "integer"
        GLOBAL_METADATA["keywords_used"].add("int")
    elif "float" in clean_type:
        result["base_type"] = "float"
        GLOBAL_METADATA["keywords_used"].add("float")
    elif "double" in clean_type:
        result["base_type"] = "double"
        GLOBAL_METADATA["keywords_used"].add("double")
    elif "bool" in clean_type:
        result["base_type"] = "boolean"
        GLOBAL_METADATA["keywords_used"].add("bool")
    elif "char" in clean_type:
        result["base_type"] = "character"
        GLOBAL_METADATA["keywords_used"].add("char")
    elif "void" in clean_type:
        result["base_type"] = "void"
        GLOBAL_METADATA["keywords_used"].add("void")
    elif "string" in clean_type.lower() or "std::string" in clean_type:
        result["base_type"] = "string"
    elif "vector" in clean_type.lower():
        result["base_type"] = "vector"
    elif "array" in clean_type.lower():
        result["base_type"] = "array"
    else:
        result["base_type"] = clean_type if clean_type else "unknown"
    
    return result

def extract_var(node):
    """Extract variable name or literal value"""
    if not isinstance(node, dict):
        return None
    
    kind = node.get("kind")
    
    if kind == "DeclRefExpr":
        return node.get("referencedDecl", {}).get("name")
    
    if kind == "IntegerLiteral":
        return node.get("value", "literal")
    
    if kind == "FloatingLiteral":
        return node.get("value", "literal")
    
    if kind == "StringLiteral":
        return f'"{node.get("value", "string")}"'
    
    if kind == "CXXBoolLiteralExpr":
        return str(node.get("value", False)).lower()
    
    if kind == "UnaryOperator":
        op = node.get("opcode")
        if op in ["++", "--"]:
            GLOBAL_METADATA["operators_used"].add(op)
        operand = extract_var(node.get("inner", [{}])[0])
        return f"{op}{operand}" if operand else None
    
    for child in node.get("inner", []):
        result = extract_var(child)
        if result is not None:
            return result
    
    return None

def extract_function_name(node):
    """Extract function name from call expression"""
    if not isinstance(node, dict):
        return None
    
    if node.get("kind") == "DeclRefExpr":
        return node.get("referencedDecl", {}).get("name")
    
    for child in node.get("inner", []):
        name = extract_function_name(child)
        if name:
            return name
    
    return None

def extract_condition(node):
    """Extract and format condition expressions"""
    if not isinstance(node, dict):
        return None
    
    kind = node.get("kind")
    
    if kind == "BinaryOperator":
        op = node.get("opcode")
        GLOBAL_METADATA["operators_used"].add(op)
        
        if op in COMPARISON_OPS or op in LOGICAL_OPS:
            lhs = extract_var(node.get("inner", [{}])[0])
            rhs = extract_var(node.get("inner", [{}, {}])[1])
            
            op_name = OPERATOR_MAP.get(op, op)
            return {
                "text": f"{lhs} {op} {rhs}",
                "natural": f"{lhs} {op_name} {rhs}",
                "operator": op,
                "lhs": lhs,
                "rhs": rhs
            }
    
    if kind == "UnaryOperator" and node.get("opcode") == "!":
        GLOBAL_METADATA["operators_used"].add("!")
        operand = extract_var(node.get("inner", [{}])[0])
        return {
            "text": f"!{operand}",
            "natural": f"not {operand}",
            "operator": "!",
            "operand": operand
        }
    
    for child in node.get("inner", []):
        cond = extract_condition(child)
        if cond:
            return cond
    
    return None

def extract_array_info(node):
    """Extract array subscript information"""
    if not isinstance(node, dict):
        return None
    
    if node.get("kind") == "ArraySubscriptExpr":
        inner = node.get("inner", [])
        if len(inner) >= 2:
            array_name = extract_var(inner[0])
            index = extract_var(inner[1])
            return {
                "array": array_name,
                "index": index,
                "notation": f"{array_name}[{index}]"
            }
    
    return None

def extract_member_access(node):
    """Extract member access (. or ->)"""
    if not isinstance(node, dict):
        return None
    
    if node.get("kind") == "MemberExpr":
        inner = node.get("inner", [])
        if inner:
            object_name = extract_var(inner[0])
            member_name = node.get("name")
            is_arrow = node.get("isArrow", False)
            operator = "->" if is_arrow else "."
            
            return {
                "object": object_name,
                "member": member_name,
                "operator": operator,
                "notation": f"{object_name}{operator}{member_name}"
            }
    
    return None

# ================= AST TRAVERSAL =================

def traverse(node, parent_kind=None):
    """Recursively traverse AST and extract features"""
    global current_function, current_target, current_scope
    
    if not isinstance(node, dict):
        if isinstance(node, list):
            for item in node:
                traverse(item, parent_kind)
        return
    
    kind = node.get("kind")
    
    # ========== INCLUDES ==========
    if kind == "IncludeDirective" or "include" in node.get("name", "").lower():
        include = node.get("name") or node.get("value")
        if include:
            GLOBAL_METADATA["includes"].append(include)
    
    # ========== NAMESPACE ==========
    if kind == "NamespaceDecl":
        namespace = node.get("name")
        if namespace:
            GLOBAL_METADATA["namespaces"].append(namespace)
            GLOBAL_METADATA["keywords_used"].add("namespace")
    
    # ========== CLASS/STRUCT ==========
    if kind in ["CXXRecordDecl", "ClassDecl", "StructDecl"]:
        class_name = node.get("name")
        if class_name:
            class_info = {
                "name": class_name,
                "type": "class" if kind == "ClassDecl" else "struct",
                "methods": [],
                "members": []
            }
            GLOBAL_METADATA["classes"].append(class_info)
            GLOBAL_METADATA["keywords_used"].add("class" if kind == "ClassDecl" else "struct")
            current_scope = f"class:{class_name}"
    
    # ========== FUNCTION DECLARATION ==========
    if kind == "FunctionDecl":
        fname = node.get("name")
        if fname and fname not in IR:
            current_function = fname
            current_scope = f"function:{fname}"
            
            GLOBAL_METADATA["functions"].append(fname)
            
            IR[fname] = {
                "name": fname,
                "return_type": normalize_type(node.get("type", {}).get("qualType")),
                "parameters": {},
                "local_variables": {},
                "actions": [],
                "control_flow": {
                    "has_loops": False,
                    "has_conditions": False,
                    "has_recursion": False
                },
                "complexity": {
                    "cyclomatic": 1,
                    "nesting_depth": 0
                },
                "keywords_used": set(),
                "operators_used": set()
            }
        elif fname:
            current_function = fname
    
    # ========== PARAMETERS ==========
    if kind == "ParmVarDecl" and current_function:
        param_name = node.get("name")
        param_type = normalize_type(node.get("type"))
        
        if param_name:
            IR[current_function]["parameters"][param_name] = param_type
    
    # ========== VARIABLE DECLARATION ==========
    if kind == "VarDecl":
        var_name = node.get("name")
        var_type = normalize_type(node.get("type"))
        
        if var_name:
            if current_function:
                IR[current_function]["local_variables"][var_name] = var_type
                
                init_expr = None
                for child in node.get("inner", []):
                    init_expr = extract_var(child)
                    if init_expr:
                        break
                
                IR[current_function]["actions"].append({
                    "type": "declaration",
                    "variable": var_name,
                    "var_type": var_type,
                    "initialized": init_expr is not None,
                    "initial_value": init_expr,
                    "natural": f"Declare {var_type['base_type']} variable '{var_name}'" + 
                               (f" initialized to {init_expr}" if init_expr else "")
                })
            else:
                GLOBAL_METADATA["global_variables"].append({
                    "name": var_name,
                    "type": var_type
                })
            
            prev_target = current_target
            current_target = var_name
            for child in node.get("inner", []):
                traverse(child, kind)
            current_target = prev_target
            return
    
    # ========== ASSIGNMENT ==========
    if kind == "BinaryOperator" and node.get("opcode") == "=":
        GLOBAL_METADATA["operators_used"].add("=")
        
        lhs_node = node.get("inner", [{}])[0]
        current_target = extract_var(lhs_node)
        array_info = extract_array_info(lhs_node)
        traverse(node.get("inner", [{}, {}])[1], kind)
        return
    
    # ========== ARITHMETIC/LOGIC OPERATIONS ==========
    if kind == "BinaryOperator":
        op = node.get("opcode")
        GLOBAL_METADATA["operators_used"].add(op)
        
        if current_function and op in OPERATOR_MAP:
            lhs = extract_var(node.get("inner", [{}])[0])
            rhs = extract_var(node.get("inner", [{}, {}])[1])
            
            IR[current_function]["operators_used"].add(op)
            
            if op in COMPARISON_OPS:
                IR[current_function]["control_flow"]["has_conditions"] = True
                if "complexity" in IR[current_function]:
                    IR[current_function]["complexity"]["cyclomatic"] += 1
            
            if op not in ["=", "+=", "-=", "*=", "/=", "%="]:
                IR[current_function]["actions"].append({
                    "type": "operation",
                    "operation": OPERATOR_MAP[op],
                    "operator": op,
                    "lhs": lhs,
                    "rhs": rhs,
                    "target": current_target,
                    "natural": f"Compute {OPERATOR_MAP[op]} of {lhs} and {rhs}" + 
                               (f" and store in {current_target}" if current_target else "")
                })
    
    # ========== UNARY OPERATIONS ==========
    if kind == "UnaryOperator":
        op = node.get("opcode")
        if op:
            GLOBAL_METADATA["operators_used"].add(op)
            if current_function:
                IR[current_function]["operators_used"].add(op)
    
    # ========== FOR LOOP ==========
    if kind == "ForStmt":
        GLOBAL_METADATA["keywords_used"].add("for")
        
        if current_function:
            IR[current_function]["keywords_used"].add("for")
            IR[current_function]["control_flow"]["has_loops"] = True
            if "complexity" in IR[current_function]:
                IR[current_function]["complexity"]["cyclomatic"] += 1
            
            inner = node.get("inner", [])
            init_expr = extract_var(inner[0]) if len(inner) > 0 else None
            condition = extract_condition(inner[1]) if len(inner) > 1 else None
            increment = extract_var(inner[2]) if len(inner) > 2 else None
            
            IR[current_function]["actions"].append({
                "type": "loop",
                "loop_type": "for",
                "initialization": init_expr,
                "condition": condition,
                "increment": increment,
                "natural": f"Iterate using for-loop" + 
                           (f" with condition {condition['natural']}" if condition else "")
            })
    
    # ========== WHILE LOOP ==========
    if kind == "WhileStmt":
        GLOBAL_METADATA["keywords_used"].add("while")
        
        if current_function:
            IR[current_function]["keywords_used"].add("while")
            IR[current_function]["control_flow"]["has_loops"] = True
            if "complexity" in IR[current_function]:
                IR[current_function]["complexity"]["cyclomatic"] += 1
            
            condition = extract_condition(node)
            
            IR[current_function]["actions"].append({
                "type": "loop",
                "loop_type": "while",
                "condition": condition,
                "natural": f"Repeat while {condition['natural']}" if condition else "Repeat while condition is true"
            })
    
    # ========== DO-WHILE LOOP ==========
    if kind == "DoStmt":
        GLOBAL_METADATA["keywords_used"].add("do")
        GLOBAL_METADATA["keywords_used"].add("while")
        
        if current_function:
            IR[current_function]["keywords_used"].add("do")
            IR[current_function]["control_flow"]["has_loops"] = True
            if "complexity" in IR[current_function]:
                IR[current_function]["complexity"]["cyclomatic"] += 1
            
            condition = extract_condition(node)
            
            IR[current_function]["actions"].append({
                "type": "loop",
                "loop_type": "do-while",
                "condition": condition,
                "natural": f"Execute at least once, then repeat while {condition['natural']}" if condition else "Execute at least once"
            })
    
    # ========== IF STATEMENT ==========
    if kind == "IfStmt":
        GLOBAL_METADATA["keywords_used"].add("if")
        
        if current_function:
            IR[current_function]["keywords_used"].add("if")
            IR[current_function]["control_flow"]["has_conditions"] = True
            if "complexity" in IR[current_function]:
                IR[current_function]["complexity"]["cyclomatic"] += 1
            
            condition = extract_condition(node)
            has_else = len(node.get("inner", [])) > 2
            
            if has_else:
                GLOBAL_METADATA["keywords_used"].add("else")
                IR[current_function]["keywords_used"].add("else")
            
            IR[current_function]["actions"].append({
                "type": "conditional",
                "conditional_type": "if",
                "condition": condition,
                "has_else": has_else,
                "natural": f"Check if {condition['natural']}" if condition else "Check condition" +
                           (" and handle alternative case" if has_else else "")
            })
    
    # ========== SWITCH STATEMENT ==========
    if kind == "SwitchStmt":
        GLOBAL_METADATA["keywords_used"].add("switch")
        
        if current_function:
            IR[current_function]["keywords_used"].add("switch")
            IR[current_function]["control_flow"]["has_conditions"] = True
            
            switch_var = extract_var(node)
            
            IR[current_function]["actions"].append({
                "type": "conditional",
                "conditional_type": "switch",
                "variable": switch_var,
                "natural": f"Branch based on value of {switch_var}"
            })
    
    # ========== CASE LABEL ==========
    if kind == "CaseStmt":
        GLOBAL_METADATA["keywords_used"].add("case")
        
        if current_function and current_function in IR and "complexity" in IR[current_function]:
            IR[current_function]["complexity"]["cyclomatic"] += 1
    
    # ========== BREAK/CONTINUE ==========
    if kind == "BreakStmt":
        GLOBAL_METADATA["keywords_used"].add("break")
        if current_function:
            IR[current_function]["actions"].append({
                "type": "control",
                "control_type": "break",
                "natural": "Exit loop or switch"
            })
    
    if kind == "ContinueStmt":
        GLOBAL_METADATA["keywords_used"].add("continue")
        if current_function:
            IR[current_function]["actions"].append({
                "type": "control",
                "control_type": "continue",
                "natural": "Skip to next iteration"
            })
    
    # ========== RETURN STATEMENT ==========
    if kind == "ReturnStmt":
        GLOBAL_METADATA["keywords_used"].add("return")
        
        if current_function:
            IR[current_function]["keywords_used"].add("return")
            
            return_value = extract_var(node)
            
            IR[current_function]["actions"].append({
                "type": "return",
                "value": return_value,
                "natural": f"Return {return_value}" if return_value else "Return from function"
            })
    
    # ========== FUNCTION CALL ==========
    if kind == "CallExpr":
        callee = extract_function_name(node)
        args = []
        
        for child in node.get("inner", []):
            arg = extract_var(child)
            if arg:
                args.append(arg)
        
        if current_function:
            if callee == current_function:
                IR[current_function]["control_flow"]["has_recursion"] = True
            
            IR[current_function]["actions"].append({
                "type": "function_call",
                "function": callee,
                "arguments": args,
                "target": current_target,
                "natural": f"Call function '{callee}'" + 
                           (f" with arguments {', '.join(map(str, args))}" if args else "") +
                           (f" and store result in {current_target}" if current_target else "")
            })
    
    # ========== ARRAY ACCESS ==========
    if kind == "ArraySubscriptExpr":
        array_info = extract_array_info(node)
        
        if current_function and array_info:
            IR[current_function]["actions"].append({
                "type": "array_access",
                "array": array_info["array"],
                "index": array_info["index"],
                "target": current_target,
                "natural": f"Access element at index {array_info['index']} of array {array_info['array']}"
            })
    
    # ========== MEMBER ACCESS ==========
    if kind == "MemberExpr":
        member_info = extract_member_access(node)
        
        if current_function and member_info:
            IR[current_function]["actions"].append({
                "type": "member_access",
                "object": member_info["object"],
                "member": member_info["member"],
                "operator": member_info["operator"],
                "natural": f"Access member '{member_info['member']}' of object '{member_info['object']}'"
            })
    
    # ========== INPUT/OUTPUT ==========
    if kind == "CXXOperatorCallExpr":
        inner = node.get("inner", [])
        if inner:
            first_child = inner[0]
            if isinstance(first_child, dict):
                op = first_child.get("name", "")
                if "operator<<" in op or "cout" in str(first_child):
                    if current_function:
                        IR[current_function]["actions"].append({
                            "type": "output",
                            "stream": "cout",
                            "natural": "Output data to console"
                        })
                elif "operator>>" in op or "cin" in str(first_child):
                    if current_function:
                        IR[current_function]["actions"].append({
                            "type": "input",
                            "stream": "cin",
                            "natural": "Read input from console"
                        })
    
    # ========== RECURSE ==========
    for key, value in node.items():
        if key != "kind":
            traverse(value, kind)

# ================= MAIN EXECUTION =================

def load_and_process():
    """Load AST and process it"""
    global AST
    
    try:
        with open("ast1.json", "r", encoding="utf-8") as f:
            AST = json.load(f)

    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in ast1.json: {e}")
        print("Make sure the file was generated correctly by Clang")
        sys.exit(1)

    except Exception as e:
        print(f"[ERROR] Failed to read ast1.json: {e}")
        sys.exit(1)
    
    if not AST:
        print("[WARNING] AST is empty. No code to analyze.")
        return
    
    print("Processing AST...")
    traverse(AST)
    
    GLOBAL_METADATA["keywords_used"] = sorted(list(GLOBAL_METADATA["keywords_used"]))
    GLOBAL_METADATA["operators_used"] = sorted(list(GLOBAL_METADATA["operators_used"]))
    
    for func_name in IR:
        IR[func_name]["keywords_used"] = sorted(list(IR[func_name]["keywords_used"]))
        IR[func_name]["operators_used"] = sorted(list(IR[func_name]["operators_used"]))

def print_human_readable():
    """Print human-readable representation"""
    print("C++ CODE ANALYSIS - INTERMEDIATE REPRESENTATION")
    print("\n[GLOBAL METADATA]")
    print("-" * 80)
    print(f"Keywords used: {', '.join(GLOBAL_METADATA['keywords_used'])}")
    print(f"Operators used: {', '.join(GLOBAL_METADATA['operators_used'])}")
    
    if GLOBAL_METADATA["includes"]:
        print(f"Includes: {', '.join(GLOBAL_METADATA['includes'])}")
    
    if GLOBAL_METADATA["namespaces"]:
        print(f"Namespaces: {', '.join(GLOBAL_METADATA['namespaces'])}")
    
    if GLOBAL_METADATA["global_variables"]:
        print(f"Global variables: {len(GLOBAL_METADATA['global_variables'])}")
    
    if GLOBAL_METADATA["classes"]:
        print(f"Classes/Structs: {', '.join([c['name'] for c in GLOBAL_METADATA['classes']])}")
    
    print(f"Functions defined: {', '.join(GLOBAL_METADATA['functions'])}")
    
    for func_name, data in IR.items():
        print(f"\n[FUNCTION: {func_name}]")
        print("-" * 80)
        
        ret_type = data["return_type"]
        print(f"Returns: {ret_type['base_type']}" + 
              (f" ({', '.join(ret_type['qualifiers'])})" if ret_type['qualifiers'] else ""))
        
        if data["parameters"]:
            print(f"\nParameters:")
            for param_name, param_type in data["parameters"].items():
                print(f"  -- {param_name}: {param_type['base_type']}" + 
                      (f" ({', '.join(param_type['qualifiers'])})" if param_type['qualifiers'] else ""))
        
        if data["local_variables"]:
            print(f"\nLocal Variables:")
            type_groups = defaultdict(list)
            for var_name, var_type in data["local_variables"].items():
                type_groups[var_type['base_type']].append(var_name)
            
            for type_name, vars in type_groups.items():
                print(f"  -- {type_name}: {', '.join(vars)}")
        
        cf = data["control_flow"]
        complexity_data = data.get("complexity", {"cyclomatic": 1, "nesting_depth": 0})
        print(f"\nControl Flow:")
        print(f"  -- Contains loops: {cf['has_loops']}")
        print(f"  -- Contains conditionals: {cf['has_conditions']}")
        print(f"  -- Is recursive: {cf['has_recursion']}")
        print(f"  -- Cyclomatic complexity: {complexity_data.get('cyclomatic', 1)}")
        
        if data["keywords_used"]:
            print(f"\nKeywords: {', '.join(data['keywords_used'])}")
        if data["operators_used"]:
            print(f"Operators: {', '.join(data['operators_used'])}")
        
        if data["actions"]:
            print(f"\nExecution Flow ({len(data['actions'])} steps):")
            for i, action in enumerate(data["actions"], 1):
                print(f"  {i}. {action['natural']}")
        
        print()

def save_json_ir():
    """Save IR as JSON for NLP processing"""
    output = {
        "metadata": GLOBAL_METADATA,
        "functions": IR
    }
    
    with open("cpp_ir_output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SUCCESS] JSON IR saved to 'cpp_ir_output.json'")

def generate_nlp_summary():
    """Generate natural language summary for each function"""
    nlp_output = {}
    
    for func_name, data in IR.items():
        summary_parts = []
        
        ret = data["return_type"]["base_type"]
        params = data["parameters"]
        
        if params:
            param_desc = ", ".join([f"{name} ({ptype['base_type']})" for name, ptype in params.items()])
            summary_parts.append(f"Function '{func_name}' takes {len(params)} parameter(s): {param_desc}")
        else:
            summary_parts.append(f"Function '{func_name}' takes no parameters")
        
        summary_parts.append(f"and returns {ret}.")
        
        if data["local_variables"]:
            var_count = len(data["local_variables"])
            summary_parts.append(f"It declares {var_count} local variable(s).")
        
        cf = data["control_flow"]
        if cf["has_loops"]:
            summary_parts.append("The function contains iterative loops.")
        if cf["has_conditions"]:
            summary_parts.append("It uses conditional branching.")
        if cf["has_recursion"]:
            summary_parts.append("The function is recursive.")
        
        if data["actions"]:
            summary_parts.append(f"The function performs {len(data['actions'])} main operations:")
            action_summary = [f"  {i}. {action['natural']}" for i, action in enumerate(data["actions"], 1)]
            summary_parts.extend(action_summary)
        
        nlp_output[func_name] = {
            "summary": " ".join(summary_parts[:4]),  # High-level summary
            "detailed_steps": summary_parts[4:] if len(summary_parts) > 4 else [],
            "complexity": data.get("complexity", {}).get("cyclomatic", 1),
            "keywords": data["keywords_used"],
            "patterns": {
                "uses_loops": cf["has_loops"],
                "uses_conditionals": cf["has_conditions"],
                "is_recursive": cf["has_recursion"]
            }
        }
    
    with open("nlp_summary.json", "w", encoding="utf-8") as f:
        json.dump(nlp_output, f, indent=2, ensure_ascii=False)
    
    print(f"[SUCCESS] NLP summary saved to 'nlp_summary.json'\n")

def run_function():
    try:
        load_and_process()
        print_human_readable()
        save_json_ir()
        generate_nlp_summary()
        
    except FileNotFoundError:
        print("\n[ERROR] File 'ast1.json' not found!")
        print("Please generate AST first using:")
        print("  clang -Xclang -ast-dump=json -fsyntax-only your_code.cpp > ast1.json")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_function()