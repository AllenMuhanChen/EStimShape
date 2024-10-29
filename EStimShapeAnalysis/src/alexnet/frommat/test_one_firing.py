import onnxruntime
import torchvision.transforms as transforms
from PIL import Image

from EStimShapeAnalysis.src.alexnet.frommat.backtrace import trace_one_activation


def get_unit_activation(model_path: str, image_path: str, unit: int, x: int, y: int):
    """Get activation of specific conv3 unit at specified location."""
    # Set up model
    session = onnxruntime.InferenceSession(model_path)

    # Set up image preprocessing
    transform = transforms.Compose([
        transforms.PILToTensor(),
        lambda x: x * 1.0
    ])

    # Load and preprocess image
    image = Image.open(image_path).convert('RGB')
    input_tensor = transform(image)
    input_tensor = input_tensor.unsqueeze(0)  # Add batch dimension

    # Get model prediction
    input_name = session.get_inputs()[0].name
    outputs = session.run(['conv3'], {input_name: input_tensor.numpy()})

    # Get specific activation
    activation = outputs[0][0, unit, x, y]
    print(f"Conv3 unit {unit} activation at ({x},{y}): {activation}")


if __name__ == "__main__":
    model_path = '/home/connorlab/PycharmProjects/EStimShape/EStimShapeAnalysis/src/alexnet/frommat/data/AlexNetONNX_with_conv3'
    image_path = '/run/user/1000/gvfs/smb-share:server=connorhome.local,share=connorhome/Allen/1729807098887091_1729806952272976.png'

    # Get activation for unit 3 at position (6,6)
    trace_one_activation(model_path, image_path, unit=3, x=6, y=6)
