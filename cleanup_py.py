import ast
import os
import sys
import re

class DocstringRemover(ast.NodeTransformer):
    def visit_Module(self, node):
        self.generic_visit(node)
        node.body = self.filter_body(node.body)
        return node

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        node.body = self.filter_body(node.body)
        return node

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        node.body = self.filter_body(node.body)
        return node

    def visit_AsyncFunctionDef(self, node):
        self.generic_visit(node)
        node.body = self.filter_body(node.body)
        return node

    def filter_body(self, body):
        new_body = []
        for stmt in body:
            # Check if it's a docstring or a standalone string expression
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                continue
            new_body.append(stmt)
        
        if not new_body:
            new_body.append(ast.Pass())
        return new_body

def clean_file(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
    except Exception as e:
        print(f"Error parsing {path}: {e}")
        return

    remover = DocstringRemover()
    new_tree = remover.visit(tree)
    
    # ast.unparse removes comments and formats the code.
    new_source = ast.unparse(new_tree)
    
    # Consolidate vertical whitespace
    # ast.unparse already does a lot of this, but we'll make sure.
    # Replace 3 or more newlines with 2 newlines (one blank line)
    new_source = re.sub(r"\n{3,}", "\n\n", new_source)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_source)

if __name__ == "__main__":
    target_dir = "zygote_injection_toolkit"
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                print(f"Cleaning {full_path}")
                clean_file(full_path)
