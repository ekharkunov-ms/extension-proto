#!/usr/bin/env python

import sys
import itertools
import json

from google.protobuf.compiler import plugin_pb2 as plugin
from google.protobuf.descriptor_pb2 import DescriptorProto, EnumDescriptorProto, FieldDescriptorProto
from google.protobuf.type_pb2 import Field

def traverse(proto_file):

    def _traverse(package, items):
        for item in items:
            yield item, package

            if isinstance(item, DescriptorProto):
                for enum in item.enum_type:
                    yield enum, package

                for nested in item.nested_type:
                    nested_package = package + item.name

                    for nested_item in _traverse(nested, nested_package):
                        yield nested_item, nested_package

    return itertools.chain(
        _traverse(proto_file.package, proto_file.enum_type),
        _traverse(proto_file.package, proto_file.message_type),
    )

def generate_code(request, response):
    messages = []
    enums = []
    files = []
    output = {
        "messages": messages,
        "enums": enums,
        "files": files,
    }
    for proto_file in request.proto_file:
        file = {
            "filename": proto_file.name,
            "filename_h": proto_file.name.replace(".proto", ".pb-c.h")
        }
        files.append(file)

        for item, package in traverse(proto_file):

            data = {
                "package": proto_file.package or '',
                "filename": proto_file.name,
                "name": item.name,
                "name_lower": item.name.lower(),
                "name_upper": item.name.upper(),
            }

            if isinstance(item, DescriptorProto):
                properties = []
                data.update({ "properties": properties })
                messages.append(data)
                for f in item.field:
                    property_type = int(f.type)
                    property =  {
                        "name": f.name,
                        "type": property_type,
                        "repeated": (f.label == FieldDescriptorProto.LABEL_REPEATED),
                        "required": (f.label == FieldDescriptorProto.LABEL_REQUIRED)
                    }

                    # https://developers.google.com/protocol-buffers/docs/proto#scalar
                    if property_type == Field.TYPE_DOUBLE:
                        property["type_lua"] = "number"
                        property["type_cpp"] = "double"
                    elif property_type == Field.TYPE_FLOAT:
                        property["type_lua"] = "number"
                        property["type_cpp"] = "float"
                    elif property_type == Field.TYPE_INT64 or property_type == Field.TYPE_SFIXED64 or property_type == Field.TYPE_SINT64:
                        property["type_lua"] = "number"
                        property["type_cpp"] = "int64_t"
                    elif property_type == Field.TYPE_INT32 or property_type == Field.TYPE_SFIXED32 or property_type == Field.TYPE_SINT32:
                        property["type_lua"] = "number"
                        property["type_cpp"] = "int32_t"
                    elif property_type == Field.TYPE_FIXED64 or property_type == Field.TYPE_UINT64:
                        property["type_lua"] = "number"
                        property["type_cpp"] = "uint64_t"
                    elif property_type == Field.TYPE_FIXED32 or property_type == Field.TYPE_UINT32:
                        property["type_lua"] = "number"
                        property["type_cpp"] = "uint32_t"
                    elif property_type == Field.TYPE_BOOL:
                        property["type_lua"] = "boolean"
                        property["type_cpp"] = "bool"
                    elif property_type == Field.TYPE_ENUM:
                        property["type_lua"] = "number"
                        property["type_cpp"] = f.type_name.replace(".", "")
                    elif property_type == Field.TYPE_STRING:
                        property["type_lua"] = "string"
                        property["type_cpp"] = "char*"
                    elif property_type == Field.TYPE_BYTES:
                        property["type_lua"] = "string"
                        property["type_cpp"] = "uint8_t*"
                    elif property_type == Field.TYPE_MESSAGE:
                        property["type_lua"] = f.type_name.replace(".", "").lower()
                        property["type_cpp"] = f.type_name.replace(".", "") + "*"
                    elif property_type == Field.TYPE_GROUP:
                        print("Unsupported type 'group'")
                    else:
                        print("Unknown property type!")
                    properties.append(property)

            elif isinstance(item, EnumDescriptorProto):
                values = []
                data.update({ "values": values })
                enums.append(data)
                for v in item.value:
                    value = {
                        "name": v.name,
                        "value": v.number
                    }
                    values.append(value)


    f = response.file.add()
    f.name = "proto.json"
    f.content = json.dumps(output, indent=4)


if __name__ == '__main__':
    # Read request message from stdin
    data = sys.stdin.buffer.read()

    # Parse request
    request = plugin.CodeGeneratorRequest()
    request.ParseFromString(data)

    # Create response
    response = plugin.CodeGeneratorResponse()

    # Generate code
    generate_code(request, response)

    # Serialise response message
    output = response.SerializeToString()

    # Write to stdout
    sys.stdout.buffer.write(output)