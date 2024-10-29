import onnx
from onnx import helper, TensorProto


def add_conv3_output(model_path: str, output_path: str) -> None:
    """Modify ONNX model to include conv3 output."""
    # Load the model
    model = onnx.load(model_path)

    # Create tensor type with shape information
    tensor_type = helper.make_tensor_type_proto(
        elem_type=TensorProto.FLOAT,
        shape=["BatchSize", 384, 13, 13]  # First dim is batch size
    )

    # Create value info (output definition)
    conv3_output = helper.make_value_info(
        name="conv3",
        type_proto=tensor_type
    )

    # Add conv3 output to graph outputs
    model.graph.output.append(conv3_output)

    # Save the modified model
    onnx.save(model, output_path)
    print(f"Saved modified model to {output_path}")

def add_backtracing_output(model_path: str, output_path: str) -> None:
    # Load the model
    model = onnx.load(model_path)

    # Dictionary of layer names and their shapes
    layer_shapes = {
        'data': [None, 3, 227, 227],           # Input image
        'data_Sub': [None, 3, 227, 227],       # After mean subtraction
        'conv1': [None, 96, 55, 55],           # After first conv
        'relu1': [None, 96, 55, 55],           # After first ReLU
        'norm1': [None, 96, 55, 55],           # After first norm
        'pool1': [None, 96, 27, 27],           # After first pool
        'conv2': [None, 256, 27, 27],          # After second conv
        'relu2': [None, 256, 27, 27],          # After second ReLU
        'norm2': [None, 256, 27, 27],          # After second norm
        'pool2': [None, 256, 13, 13],          # After second pool
        'conv3': [None, 384, 13, 13],          # After third conv
    }

    # Create output for each layer
    outputs = []
    for name, shape in layer_shapes.items():
        # Replace None with "BatchSize" for dynamic batch dimension
        tensor_shape = ["BatchSize" if s is None else s for s in shape]

        # Create tensor type
        tensor_type = helper.make_tensor_type_proto(
            elem_type=TensorProto.FLOAT,
            shape=tensor_shape
        )

        # Create value info for this layer
        layer_output = helper.make_value_info(
            name=name,
            type_proto=tensor_type
        )
        outputs.append(layer_output)

    # Add all outputs to model
    model.graph.output.extend(outputs)

    # Save modified model
    onnx.save(model, output_path)
    print(f"Saved modified model with all layer outputs to {output_path}")

    # Print info about outputs
    print("\nAdded outputs:")
    for output in outputs:
        print(f"- {output.name}")
        shape = [str(dim.dim_param) if dim.dim_param else str(dim.dim_value)
                for dim in output.type.tensor_type.shape.dim]
        print(f"  Shape: {shape}")

    onnx.save(model, output_path)
    print(f"Saved modified model to {output_path}")



if __name__ == "__main__":
    input_model_path = '/home/connorlab/PycharmProjects/EStimShape/EStimShapeAnalysis/src/alexnet/frommat/data/AlexNetONNX'
    output_model_path = '/home/connorlab/PycharmProjects/EStimShape/EStimShapeAnalysis/src/alexnet/frommat/data/AlexNetONNX_with_conv3'

    # Add conv3 output
    add_backtracing_output(input_model_path, output_model_path)

    # Print info about modified model
    print("\nModified model information:")
    modified_model = onnx.load(output_model_path)
    print("\nOutputs:")
    for output in modified_model.graph.output:
        print(f"- {output.name}")
        print(f"  Shape: {[dim for dim in output.type.tensor_type.shape.dim]}")