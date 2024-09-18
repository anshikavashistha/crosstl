from ..ast import (
    ShaderNode,
    AssignmentNode,
    FunctionNode,
    ReturnNode,
    BinaryOpNode,
    UnaryOpNode,
    IfNode,
    ForNode,
    VariableNode,
    FunctionCallNode,
    MemberAccessNode,
    VERTEXShaderNode,
    FRAGMENTShaderNode,
    TernaryOpNode,
)


class HLSLCodeGen:
    def __init__(self):
        self.current_shader = None
        self.vertex_item = None
        self.fragment_item = None
        self.gl_position = False
        self.type_mapping = {
            "void": "void",
            "vec2": "float2",
            "vec3": "float3",
            "vec4": "float4",
            "mat2": "float2x2",
            "mat3": "float3x3",
            "mat4": "float4x4",
            "int": "int",
            "ivec2": "int2",
            "ivec3": "int3",
            "ivec4": "int4",
            "uint": "uint",
            "uvec2": "uint2",
            "uvec3": "uint3",
            "uvec4": "uint4",
            "bool": "bool",
            "bvec2": "bool2",
            "bvec3": "bool3",
            "bvec4": "bool4",
            "float": "float",
            "double": "double",
            "sampler2D": "Texture2D",
            "samplerCube": "TextureCube",
        }

    def generate(self, ast):
        if isinstance(ast, ShaderNode):
            self.current_shader = ast
            return self.generate_shader(ast)
        return ""

    def generate_shader(self, node):
        self.shader_inputs = node.global_inputs
        self.shader_outputs = node.global_outputs
        code = "\n"
        # Generate global inputs and outputs
        if self.shader_inputs:
            code += "struct VSINPUT {\n"
            for i, (vtype, name) in enumerate(self.shader_inputs):
                if i >= 1:
                    code += f"    {self.map_type(vtype)} {name} : TEXCOORD{i};\n"
                else:
                    code += f"    {self.map_type(vtype)} {name} : POSITION{i};\n"
            code += "};\n\n"

        if self.shader_outputs:
            code += "struct VSOUTPUT {\n"
            for i, (vtype, name) in enumerate(self.shader_outputs):
                code += f"    {self.map_type(vtype)} {name} : SV_TARGET{i};\n"
            code += "};\n\n"

        # Generate functions
        for function in node.global_functions:
            code += self.generate_function(function, "global") + "\n"

        # Generate vertex shader section
        self.vertex_item = node.vertex_section
        if isinstance(self.vertex_item, VERTEXShaderNode):
            shader_type = "vertex"
            self.check_gl_position(self.vertex_item)
            if self.vertex_item.inputs:
                code += "struct VSInput {\n"
                for i, (vtype, name) in enumerate(self.vertex_item.inputs):
                    if i >= 1:
                        code += f"    {self.map_type(vtype)} {name} : TEXCOORD{i-1};\n"
                    else:
                        code += f"    {self.map_type(vtype)} {name} : POSITION;\n"
                code += "};\n\n"
            if self.vertex_item.outputs:
                code += "struct VSOutput {\n"
                for i, (vtype, name) in enumerate(self.vertex_item.outputs):
                    if self.gl_position:
                        code += f"   float4 position : SV_POSITION;\n"
                        self.gl_position = False
                    code += f"    {self.map_type(vtype)} {name} : TEXCOORD{i};\n"
                code += "};\n\n"

            if self.vertex_item.functions:
                code += f"{self.generate_function(self.vertex_item.functions, shader_type)}\n"

            if self.vertex_item.intermidiate:
                code += f"{self.generate_intermidiate(self.vertex_item.intermidiate, shader_type)}\n"
            if self.vertex_item.functions:
                for function_node in self.vertex_item.functions:
                    if function_node.name == "main":
                        code += f"{self.generate_main(function_node, shader_type)}\n"

        # Generate fragment shader section
        self.fragment_item = node.fragment_section
        if isinstance(self.fragment_item, FRAGMENTShaderNode):
            shader_type = "fragment"
            if self.fragment_item.inputs:
                code += "struct PSInput {\n"
                for i, (vtype, name) in enumerate(self.fragment_item.inputs):
                    code += f"    {self.map_type(vtype)} {name} : TEXCOORD{i};\n"
                code += "};\n\n"
            if self.fragment_item.outputs:
                code += "struct PSOutput {\n"
                for i, (vtype, name) in enumerate(self.fragment_item.outputs):
                    code += f"    {self.map_type(vtype)} {name} : SV_TARGET{i};\n"
                code += "};\n\n"

            if self.fragment_item.functions:
                code += f"{self.generate_function(self.fragment_item.functions, shader_type)}\n"
            if self.fragment_item.intermidiate:
                code += f"{self.generate_intermidiate(self.fragment_item.intermidiate, shader_type)}\n"
            if self.fragment_item.functions:
                for function_node in self.fragment_item.functions:
                    if function_node.name == "main":
                        code += f"{self.generate_main(function_node, shader_type)}\n"
        return code

    def check_gl_position(self, node):
        for function_node in self.vertex_item.functions:
            for stmt in function_node.body:
                vb_name = self.generate_statement(stmt)
                vb_left = vb_name.split("=")[0].strip()
                if vb_left == "output.position":
                    self.gl_position = True

    def generate_intermidiate(self, node, shader_type):
        code = ""
        for stmt in node:
            code += self.generate_statement(stmt, 0, shader_type=shader_type)
        return code

    def generate_function(self, node, shader_type):
        code = ""
        if shader_type == "vertex":
            for function_node in node:
                if function_node.name != "main":
                    params = ", ".join(
                        f"{self.map_type(param[0])} {param[1]}"
                        for param in function_node.params
                    )
                    return_type = self.map_type(function_node.return_type)
                    code += f"{return_type} {function_node.name}({params}) {{\n"

                    for stmt in function_node.body:
                        code += self.generate_statement(
                            stmt, 1, shader_type=shader_type
                        )

                    code += "}\n"
        elif shader_type == "fragment":
            for function_node in node:
                if function_node.name != "main":
                    params = ", ".join(
                        f"{self.map_type(param[0])} {param[1]}"
                        for param in function_node.params
                    )
                    return_type = self.map_type(function_node.return_type)
                    code += f"{return_type} {function_node.name}({params}) {{\n"

                    for stmt in function_node.body:
                        code += self.generate_statement(
                            stmt, 1, shader_type=shader_type
                        )
                    code += "}\n"
        elif shader_type == "global":
            if node.name == "main":
                params = "Global_INPUT input"
                return_type = "Global_OUTPUT"
            else:
                params = ", ".join(
                    f"{self.map_type(param[0])} {param[1]}" for param in node.params
                )
                return_type = self.map_type(node.return_type)

            code += f"{return_type} {node.name}({params}) {{\n"
            if node.name == "main":
                code += "    Global_OUTPUT output;\n"
            for stmt in node.body:
                code += self.generate_statement(stmt, 1, shader_type=shader_type)
            if node.name == "main":
                code += "    return output;\n"
            code += "}\n"
        return code

    def generate_main(self, node, shader_type):
        if shader_type == "vertex":
            code = "VSOutput VSMain(VSInput input) {\n"
            code += "    VSOutput output;\n"
        elif shader_type == "fragment":
            code = "PSOutput PSMain(PSInput input) {\n"
            code += "    PSOutput output;\n"
        for stmt in node.body:
            code += self.generate_statement(stmt, 1, shader_type)

        code += "    return output;\n"
        code += "}\n"
        return code

    def generate_statement(self, stmt, indent=0, shader_type=None):
        indent_str = "    " * indent
        if isinstance(stmt, VariableNode):
            return f"{indent_str}{self.map_type(stmt.vtype)} {stmt.name};\n"
        elif isinstance(stmt, AssignmentNode):
            return f"{indent_str}{self.generate_assignment(stmt, shader_type)};\n"
        elif isinstance(stmt, IfNode):
            return self.generate_if(stmt, indent, shader_type)
        elif isinstance(stmt, ForNode):
            return self.generate_for(stmt, indent, shader_type)
        elif isinstance(stmt, ReturnNode):
            code = ""
            for i, return_stmt in enumerate(stmt.value):
                code += f"{self.generate_expression(return_stmt, shader_type)}"
                if i < len(stmt.value) - 1:
                    code += ", "
            return f"{indent_str}return {code};\n"
        else:
            return f"{indent_str}{self.generate_expression(stmt, shader_type)};\n"

    def generate_assignment(self, node, shader_type=None):
        if shader_type in ["vertex", "fragment"] and isinstance(node.name, str):
            if node.name in [
                output[1] for output in getattr(self, f"{shader_type}_item").outputs
            ]:
                return f"output.{node.name} = {self.generate_expression(node.value, shader_type)}"
        if isinstance(node.name, VariableNode) and node.name.vtype:
            return f"{self.map_type(node.name.vtype)} {node.name.name} = {self.generate_expression(node.value, shader_type)}"
        else:
            lhs = self.generate_expression(node.name, shader_type)
            if lhs == "gl_Position" or lhs == "gl_position":
                return f"output.position = {self.generate_expression(node.value, shader_type)}"
            return f"{lhs} = {self.generate_expression(node.value, shader_type)}"

    def generate_if(self, node, indent, shader_type=None):
        indent_str = "    " * indent
        code = f"{indent_str}if ({self.generate_expression(node.if_condition, shader_type)}) {{\n"
        for stmt in node.if_body:
            code += self.generate_statement(stmt, indent + 1, shader_type)
        code += f"{indent_str}}}"

        for else_if_condition, else_if_body in zip(
            node.else_if_conditions, node.else_if_bodies
        ):
            code += f" else if ({self.generate_expression(else_if_condition, shader_type)}) {{\n"
            for stmt in else_if_body:
                code += self.generate_statement(stmt, indent + 1, shader_type)
            code += f"{indent_str}}}"

        if node.else_body:
            code += " else {\n"
            for stmt in node.else_body:
                code += self.generate_statement(stmt, indent + 1, shader_type)
            code += f"{indent_str}}}"
        code += "\n"
        return code

    def generate_for(self, node, indent, shader_type=None):
        indent_str = "    " * indent

        init = self.generate_statement(node.init, 0, shader_type).strip()[
            :-1
        ]  # Remove trailing semicolon

        condition = self.generate_statement(node.condition, 0, shader_type).strip()[
            :-1
        ]  # Remove trailing semicolon

        update = self.generate_statement(node.update, 0, shader_type).strip()[:-1]

        code = f"{indent_str}for ({init}; {condition}; {update}) {{\n"
        for stmt in node.body:
            code += self.generate_statement(stmt, indent + 1, shader_type)
        code += f"{indent_str}}}\n"
        return code

    def generate_expression(self, expr, shader_type=None):
        if isinstance(expr, str):
            return self.translate_expression(expr, shader_type)
        elif isinstance(expr, VariableNode):
            if isinstance(expr.name, str):
                return f"{self.map_type(expr.vtype)} {self.translate_expression(expr.name, shader_type)}"
            else:
                return f"{self.map_type(expr.vtype)} {self.generate_expression(expr.name, shader_type)}"
        elif isinstance(expr, BinaryOpNode):
            return f"{self.generate_expression(expr.left, shader_type)} {self.map_operator(expr.op)} {self.generate_expression(expr.right, shader_type)}"
        elif isinstance(expr, FunctionCallNode):
            args = ", ".join(
                self.generate_expression(arg, shader_type) for arg in expr.args
            )
            if expr.name in self.type_mapping.keys():
                return f"{self.map_type(expr.name)}({args})"
            else:
                func_name = self.translate_expression(expr.name, shader_type)
                return f"{func_name}({args})"
        elif isinstance(expr, UnaryOpNode):
            return f"{self.map_operator(expr.op)} {self.generate_expression(expr.operand, shader_type)}"
        elif isinstance(expr, TernaryOpNode):
            return f"{self.generate_expression(expr.condition, shader_type)} ? {self.generate_expression(expr.true_expr, shader_type)} : {self.generate_expression(expr.false_expr, shader_type)}"
        elif isinstance(expr, MemberAccessNode):
            return f"{self.generate_expression(expr.object, shader_type)}.{expr.member}"
        else:
            return str(expr)

    def translate_expression(self, expr, shader_type):
        if shader_type == "vertex":
            if self.vertex_item and self.vertex_item.inputs:
                for _, input_name in self.vertex_item.inputs:
                    if expr == input_name:
                        return f"input.{input_name}"
            if self.vertex_item and self.vertex_item.outputs:
                for _, output_name in self.vertex_item.outputs:
                    if expr == output_name:
                        return f"output.{output_name}"
        elif shader_type == "fragment":
            if self.fragment_item and self.fragment_item.inputs:
                for _, input_name in self.fragment_item.inputs:
                    if expr == input_name:
                        return f"input.{input_name}"
            if self.fragment_item and self.fragment_item.outputs:
                for _, output_name in self.fragment_item.outputs:
                    if expr == output_name:
                        return f"output.{output_name}"

        return self.type_mapping.get(expr, expr)

    def map_type(self, vtype):
        if vtype == "":
            return ""
        else:
            return self.type_mapping.get(vtype, vtype)

    def map_operator(self, op):
        op_map = {
            "PLUS": "+",
            "MINUS": "-",
            "MULTIPLY": "*",
            "DIVIDE": "/",
            "BITWISE_XOR": "^",
            "LESS_THAN": "<",
            "GREATER_THAN": ">",
            "ASSIGN_ADD": "+=",
            "ASSIGN_SUB": "-=",
            "ASSIGN_MUL": "*=",
            "ASSIGN_DIV": "/=",
            "ASSIGN_MOD": "%=",
            "ASSIGN_AND": "&=",
            "LOGICAL_AND": "&&",
            "LESS_EQUAL": "<=",
            "GREATER_EQUAL": ">=",
            "EQUAL": "==",
            "NOT_EQUAL": "!=",
            "AND": "&&",
            "OR": "||",
            "EQUALS": "=",
            "ASSIGN_SHIFT_LEFT": "<<=",
        }
        return op_map.get(op, op)
