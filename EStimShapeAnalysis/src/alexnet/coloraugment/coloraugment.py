import torch
import numpy as np
from PIL.Image import Image
from torchvision import transforms


class PCAAugmentation(object):
    def __init__(self, alphastd=0.1):
        self.alphastd = alphastd

    def __call__(self, img):
        if self.alphastd == 0:
            return img

        original_type = type(img)

        # Convert to tensor if it's a PIL Image
        if isinstance(img, Image):
            img = transforms.ToTensor()(img)
            was_pil = True
        else:
            was_pil = False

        # Ensure the image is a 3-channel image
        if img.dim() == 2:  # If it's a single-channel image
            img = img.unsqueeze(0)
        assert img.size(0) == 3, "Image must have 3 channels"

        # Flatten the image
        orig_size = img.size()
        img_flat = img.view(3, -1)

        # Step 1: Compute the covariance matrix of RGB pixel values
        cov = torch.mm(img_flat, img_flat.t()) / (img_flat.size(1) - 1)

        # Step 2: Compute eigenvectors and eigenvalues
        eigvals, eigvecs = torch.linalg.eigh(cov)

        # Step 3: Sort eigenvectors by eigenvalues in descending order
        idx = torch.argsort(eigvals, descending=True)
        eigvals = eigvals[idx]
        eigvecs = eigvecs[:, idx]

        # Step 4: Sample random values
        alpha = torch.randn(3) * self.alphastd

        # Step 5: Compute the color offset
        rgb_offset = torch.sum(eigvecs * (alpha * eigvals), dim=1)

        # Step 6: Apply the offset to the image
        img_augmented = img + rgb_offset.view(3, 1, 1)

        # Ensure the values are still in the valid range [0, 1]
        img_augmented = torch.clamp(img_augmented, 0, 1)

        # Reshape back to original size
        img_augmented = img_augmented.view(orig_size)

        # Convert back to PIL if the input was PIL
        if was_pil:
            img_augmented = transforms.ToPILImage()(img_augmented)

        return img_augmented


import torch
import torchvision
import matplotlib.pyplot as plt
from torchvision import transforms



# Assuming AparicoColorAugmentation is in the same file, otherwise import it
# from your_module import AparicoColorAugmentation

def visualize_augmentation(image, augmented_images, title):
    fig, axes = plt.subplots(1, 6, figsize=(20, 4))
    axes[0].imshow(image)
    axes[0].set_title('Original')
    axes[0].axis('off')
    for i, aug_img in enumerate(augmented_images):
        axes[i + 1].imshow(aug_img)
        axes[i + 1].set_title(f'Aug {i + 1}')
        axes[i + 1].axis('off')
    plt.suptitle(title)
    plt.show()


def test_aparico_color_augmentation():
    # Load a small subset of CIFAR-10 for testing
    dataset = torchvision.datasets.CIFAR10(root='./data', train=True, download=True, transform=transforms.ToTensor())

    # Create Aparico Color Augmentation
    aparico_transform = PCAAugmentation(alphastd=0.1)

    # Test on a few sample images
    num_samples = 5
    sample_images = [dataset[i][0] for i in range(num_samples)]

    for i, img in enumerate(sample_images):
        # Apply augmentation multiple times
        augmented_images = [aparico_transform(img.clone()) for _ in range(5)]

        # Convert tensors to numpy arrays for visualization
        original_img = img.permute(1, 2, 0).numpy()
        augmented_imgs = [aug_img.permute(1, 2, 0).numpy() for aug_img in augmented_images]

        # Visualize
        visualize_augmentation(original_img, augmented_imgs, f'Sample {i + 1}')

    # Test with different alphastd values
    img = sample_images[0]
    alphastd_values = [0.1, 0.1, 0.1, 0.1, 0.1]

    augmented_images = []
    for alphastd in alphastd_values:
        aparico_transform = PCAAugmentation(alphastd=alphastd)
        augmented_images.append(aparico_transform(img.clone()).permute(1, 2, 0).numpy())

    visualize_augmentation(img.permute(1, 2, 0).numpy(), augmented_images, 'Different alphastd values')


if __name__ == "__main__":
    test_aparico_color_augmentation()