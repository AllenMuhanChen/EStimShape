import torch
import torchvision.transforms as transforms
from PIL import Image
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
class ShapePreprocessTransform(torch.nn.Module):
    """
    Custom transform for preprocessing shape images with gray backgrounds.
    Finds the bounding box of the shape, scales it to a target size,
    and centers it in a gray background.
    """

    def __init__(self, target_size: int = 227, bbox_scale: float = 0.5, background_value: int = 127):
        super().__init__()
        self.target_size = target_size
        self.bbox_scale = bbox_scale
        self.background_value = background_value

        # Standard tensor conversion
        self.to_tensor = transforms.PILToTensor()

    def find_foreground_bbox(self, img: Image.Image) -> tuple[int, int, int, int]:
        """Find bounding box of non-background pixels."""
        img_array = np.array(img)
        mask = ~(((img_array[..., 0] == self.background_value) &
                  (img_array[..., 1] == self.background_value) &
                  (img_array[..., 2] == self.background_value)) |
                 ((img_array[..., 0] == self.background_value + 1) &
                  (img_array[..., 1] == self.background_value + 1) &
                  (img_array[..., 2] == self.background_value + 1)))

        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        ymin, ymax = np.where(rows)[0][[0, -1]]
        xmin, xmax = np.where(cols)[0][[0, -1]]

        return xmin, ymin, xmax, ymax

    def forward(self, img: Image.Image) -> torch.Tensor:
        """Process the image and return tensor."""
        # Find and crop to bounding box
        left, top, right, bottom = self.find_foreground_bbox(img)
        cropped = img.crop((left, top, right, bottom))

        # Calculate dimensions for scaling
        bbox_width = right - left
        bbox_height = bottom - top
        max_dim = max(bbox_width, bbox_height)

        # Add padding to make square
        pad_width = (max_dim - bbox_width) // 2
        pad_height = (max_dim - bbox_height) // 2
        square_img = Image.new('RGB', (max_dim, max_dim),
                               (self.background_value,) * 3)
        square_img.paste(cropped, (pad_width, pad_height))

        # Calculate final scaled size and padding
        scale_size = int(self.target_size * self.bbox_scale)
        final_pad = (self.target_size - scale_size) // 2

        # Create final image
        final_img = Image.new('RGB', (self.target_size, self.target_size),
                              (self.background_value,) * 3)
        scaled_img = square_img.resize((scale_size, scale_size),
                                       Image.Resampling.LANCZOS)
        final_img.paste(scaled_img, (final_pad, final_pad))

        # Convert to tensor
        tensor = self.to_tensor(final_img)
        return tensor.float()

def main():
    from src.pga.alexnet import alexnet_context

    # Set up paths
    test_dir = Path("/home/r2_allen/Documents/EStimShape") / alexnet_context.ga_database / "stimuli/ga/pngs"
    output_dir = Path("/home/r2_allen/Documents/EStimShape") / alexnet_context.ga_database / "transform_test"
    output_dir.mkdir(exist_ok=True)

    # Get sample images
    test_images = list(test_dir.glob("*.png"))[:3]  # Test first 3 images

    # Create transforms with different scales
    scales = [0.3, 0.5, 0.7]
    transforms_to_test = [ShapePreprocessTransform(bbox_scale=scale) for scale in scales]

    # Set up visualization
    n_rows = len(test_images)
    n_cols = len(scales) + 1  # +1 for original image
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 4 * n_rows))

    # For converting tensors back to images
    to_pil = transforms.ToPILImage()

    # Process each image
    for row, img_path in enumerate(test_images):
        # Load and display original
        original = Image.open(img_path).convert('RGB')
        axes[row, 0].imshow(original)
        axes[row, 0].set_title('Original')
        axes[row, 0].axis('off')

        # Process and display transformed versions
        for col, (transform, scale) in enumerate(zip(transforms_to_test, scales), 1):
            processed = transform(original)
            processed_img = to_pil(processed)

            axes[row, col].imshow(processed_img)
            axes[row, col].set_title(f'Scale {scale}')
            axes[row, col].axis('off')

    plt.tight_layout()
    plt.savefig(output_dir / "transform_visualization.png")
    print(f"Visualization saved to {output_dir}/transform_visualization.png")
    plt.close()

if __name__ == '__main__':
    main()