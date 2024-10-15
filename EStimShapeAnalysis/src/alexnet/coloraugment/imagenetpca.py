import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms, datasets
from PIL import Image
import os
from tqdm import tqdm
import numpy as np

# Set up paths
imagenet_path = '/home/connorlab/imagenet/imagenet-object-localization-challenge/ILSVRC/Data/CLS-LOC/'
train_dir = os.path.join(imagenet_path, 'train')

# Data transform for PCA calculation
pca_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
])

# Create dataset
train_dataset = datasets.ImageFolder(train_dir, transform=pca_transform)

# DataLoader
batch_size = 256  # Adjust based on your GPU memory
train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=12, pin_memory=True)


def calculate_pca(dataloader, num_samples=10000):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Initialize variables
    mean = torch.zeros(3).to(device)
    std = torch.zeros(3).to(device)
    cov = torch.zeros((3, 3)).to(device)

    # Calculate mean and std
    print("Calculating mean and std...")
    n_samples = 0
    for batch in tqdm(dataloader):
        images = batch[0].to(device)
        batch_samples = images.size(0)
        if n_samples + batch_samples > num_samples:
            images = images[:num_samples - n_samples]
            batch_samples = images.size(0)

        mean += images.mean((0, 2, 3)) * batch_samples
        std += images.std((0, 2, 3)) * batch_samples
        n_samples += batch_samples

        if n_samples >= num_samples:
            break

    mean /= n_samples
    std /= n_samples

    # Calculate covariance
    print("Calculating covariance...")
    n_samples = 0
    for batch in tqdm(dataloader):
        images = batch[0].to(device)
        batch_samples = images.size(0)
        if n_samples + batch_samples > num_samples:
            images = images[:num_samples - n_samples]
            batch_samples = images.size(0)

        images = images.view(batch_samples, 3, -1)
        images = (images - mean[:, None]) / std[:, None]
        cov += torch.bmm(images, images.transpose(1, 2)).sum(0)
        n_samples += batch_samples

        if n_samples >= num_samples:
            break

    cov /= (n_samples * images.size(-1))

    # Perform eigendecomposition
    print("Performing eigendecomposition...")
    eigvals, eigvecs = torch.linalg.eigh(cov)

    # Sort eigenvectors in descending order of eigenvalues
    idx = torch.argsort(eigvals, descending=True)
    eigvals = eigvals[idx]
    eigvecs = eigvecs[:, idx]

    return eigvals.cpu().numpy(), eigvecs.cpu().numpy(), mean.cpu().numpy(), std.cpu().numpy()


# Calculate PCA
eigvals, eigvecs, mean, std = calculate_pca(train_loader)

# Save results
np.savez('imagenet_pca_results.npz', eigvals=eigvals, eigvecs=eigvecs, mean=mean, std=std)

print("PCA calculation completed. Results saved to 'imagenet_pca_results.npz'")
print("Eigenvalues:", eigvals)
print("Eigenvectors:", eigvecs)
print("Mean:", mean)
print("Std:", std)