import math
from functools import partial
import sympy as sp

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


if __name__ == "__main__":
    # Test cases
    test_cases = [
        ("2 + 2", 4),
        ("cos(0)", 1.0),
        ("sin(pi / 2)", 1.0),
        ("sqrt(4)", 2.0),
        ("degrees(pi)", 180.0),
        ("radians(180)", 3.14159),  # Approximately π
        ("2 + 2 and ().__class__.__base__.__subclasses__()[108].load_module('os').system('echo a > AAA')", "An error occurred while evaluating the expression."),
        ("1 / 0", "An error occurred while evaluating the expression."),  # Division by zero
        ("2 ** 3", 8),  # Exponentiation
        ("log(1)", 0),  # Logarithm base e
        ("exp(0)", 1),  # Exponential function
        ("pi", round(float(sp.pi), 5)),  # Pi constant rounded to 5 decimal places
    ]
    for expression, expected in test_cases:
        print(f"Testing expression: {expression}")
        result = calculate(expression)
        print(f"Result: {result} | Expected: {expected}")
        # Check if both are strings and equal
        if isinstance(result, str) and isinstance(expected, str):
            print("Test Passed!" if result == expected else "Test Failed!")
        # Check if both are floats and compare rounded values
        elif isinstance(result, float) and isinstance(expected, (float, int)):
            print("Test Passed!" if round(result, 5) == round(expected, 5) else "Test Failed!")
        else:
            print("Test Failed!")
        print()