import onnxruntime
import torchvision.transforms as transforms
from PIL import Image
import numpy as np
from typing import List, Tuple


def analyze_conv3_units(model_path: str, image_path: str, top_n: int = 10) -> List[Tuple[Tuple[int, int, int], float]]:
    """Analyze all conv3 units and return top N activations with their locations."""
    # Set up model
    session = onnxruntime.InferenceSession(model_path)

    # Set up image preprocessing
    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(227),  # AlexNet from MATLAB uses 227x227
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    # Load and preprocess image
    image = Image.open(image_path).convert('RGB')
    input_tensor = transform(image)
    input_tensor = input_tensor.unsqueeze(0)  # Add batch dimension

    # Get conv3 activations
    input_name = session.get_inputs()[0].name
    outputs = session.run(['conv3'], {input_name: input_tensor.numpy()})
    conv3_features = outputs[0]  # Shape [1, 384, 13, 13]

    # Find top activations across all units and locations
    activations = []

    # Iterate through all units and spatial locations
    for unit in range(conv3_features.shape[1]):  # 384 units
        for x in range(conv3_features.shape[2]):  # 13 spatial locations
            for y in range(conv3_features.shape[3]):  # 13 spatial locations
                activation = float(conv3_features[0, unit, x, y])
                activations.append(((unit, x, y), activation))

    # Sort by activation value and get top N
    top_activations = sorted(activations, key=lambda x: x[1], reverse=True)[:top_n]

    # Print results
    print(f"\nTop {top_n} activations across all conv3 units:")
    print("-" * 50)
    for (unit, x, y), activation in top_activations:
        print(f"Unit {unit:3d} at location ({x:2d},{y:2d}): {activation:8.3f}")

    # Print unit-wise maximum activations
    print("\nHighest activation per unit (top 10 units):")
    print("-" * 50)
    unit_max_activations = []
    for unit in range(conv3_features.shape[1]):
        max_activation = float(conv3_features[0, unit].max())
        unit_max_activations.append((unit, max_activation))

    top_units = sorted(unit_max_activations, key=lambda x: x[1], reverse=True)[:10]
    for unit, activation in top_units:
        print(f"Unit {unit:3d}: {activation:8.3f}")

    return top_activations


if __name__ == "__main__":
    model_path = '/home/connorlab/PycharmProjects/EStimShape/EStimShapeAnalysis/src/alexnet/frommat/data/AlexNetONNX_with_conv3'
    image_path = '/run/user/1000/gvfs/smb-share:server=connorhome.local,share=connorhome/Allen/1729807098887091_1729806952272976.png'

    analyze_conv3_units(model_path, image_path, top_n=20)