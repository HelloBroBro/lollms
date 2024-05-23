import math
from functools import partial

def calculate(expression: str) -> float:    
    try:
        # Add the math module functions to the local namespace
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        
        # Evaluate the expression safely using the allowed names
        result = eval(expression, {"__builtins__": None}, allowed_names)
        return result
    except Exception as e:
        return str(e)
    

def calculate_function(processor, client):
    return {
        "function_name": "calculate",
        "function": calculate,
        "function_description": "Whenever you need to perform mathematic computations, you can call this function with the math expression and you will get the answer.",
        "function_parameters": [{"name": "expression", "type": "str"}]                
    }