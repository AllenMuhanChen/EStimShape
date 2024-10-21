import onnx
import onnxruntime


def load_onnx_model(model_path):
    # Load the ONNX model
    onnx_model = onnx.load(model_path)
    return onnx_model


def print_model_info(onnx_model):
    print("Model inputs:")
    for input in onnx_model.graph.input:
        print(f"- {input.name}")

    print("\nModel outputs:")
    for output in onnx_model.graph.output:
        print(f"- {output.name}")

    print("\nInitializers (weights and biases):")
    for initializer in onnx_model.graph.initializer:
        print(f"- {initializer.name}: shape {initializer.dims}")

    print("\nNodes (operations):")
    for node in onnx_model.graph.node:
        print(f"- {node.op_type}: {node.name}")
        print(f"  Inputs: {node.input}")
        print(f"  Outputs: {node.output}")
        print()


# Load the ONNX model
model_path = '/home/connorlab/PycharmProjects/EStimShape/EStimShapeAnalysis/src/alexnet/frommat/data/AlexNetONNX'  # Update this to your ONNX model's path
onnx_model = load_onnx_model(model_path)

# Print model information
print_model_info(onnx_model)

# Print input and output shapes using onnxruntime
session = onnxruntime.InferenceSession(model_path)
print("\nInput shapes:")
for input in session.get_inputs():
    print(f"- {input.name}: {input.shape}")

print("\nOutput shapes:")
for output in session.get_outputs():
    print(f"- {output.name}: {output.shape}")