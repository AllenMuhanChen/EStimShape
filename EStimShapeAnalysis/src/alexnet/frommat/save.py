import onnx
import shutil
import os


def load_and_save_onnx_model(input_path, output_path):
    # Load the ONNX model
    onnx_model = onnx.load(input_path)

    # Verify the model
    onnx.checker.check_model(onnx_model)

    # Save the model
    onnx.save(onnx_model, output_path)

    print(f"Model saved to {output_path}")


def copy_onnx_model(input_path, output_path):
    # Simply copy the ONNX file
    shutil.copy2(input_path, output_path)
    print(f"Model copied to {output_path}")


if __name__ == "__main__":
    input_model_path = '/home/connorlab/PycharmProjects/EStimShape/EStimShapeAnalysis/src/alexnet/frommat/data/AlexNetONNX'
    output_model_path = 'lightweight_alexnet.onnx'

    # Option 1: Load and save (allows for potential optimizations)
    load_and_save_onnx_model(input_model_path, output_model_path)

    # Option 2: Simply copy the file (fastest, if no optimizations needed)
    # copy_onnx_model(input_model_path, output_model_path)

    # Print model size
    print(f"Model size: {os.path.getsize(output_model_path) / (1024 * 1024):.2f} MB")