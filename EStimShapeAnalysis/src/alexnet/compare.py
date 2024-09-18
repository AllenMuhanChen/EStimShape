import torch
import torch.nn as nn
from torchvision import models, datasets, transforms
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt

from EStimShapeAnalysis.src.alexnet.standardalexnet_cifar import CustomAlexNet
from alexnetparallelgpus import AlexNetGPUSimulated
import os

# Set device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def visualize_filters(parallel_model, standard_model):
    weights_gpu1 = parallel_model.features_gpu1_1[0].weight.data.cpu()
    weights_gpu2 = parallel_model.features_gpu2_1[0].weight.data.cpu()
    weights_standard = standard_model.features[0].weight.data.cpu()

    # Normalize weights
    def normalize(w):
        return (w - w.min()) / (w.max() - w.min())

    weights_gpu1 = normalize(weights_gpu1)
    weights_gpu2 = normalize(weights_gpu2)
    weights_standard = normalize(weights_standard)

    def plot_filters(weights, title):
        num_filters = weights.shape[0]
        if num_filters == 48:
            num_rows, num_cols = 6, 8
        else:  # for 96 filters
            num_rows, num_cols = 8, 12

        fig, axes = plt.subplots(num_rows, num_cols, figsize=(20, 15))
        fig.suptitle(title, fontsize=16)

        for i in range(num_filters):
            row = i // num_cols
            col = i % num_cols
            axes[row, col].imshow(weights[i].permute(1, 2, 0))
            axes[row, col].axis('off')

        # Turn off any unused subplots
        for i in range(num_filters, num_rows * num_cols):
            row = i // num_cols
            col = i % num_cols
            axes[row, col].axis('off')

        plt.tight_layout()
        return fig

    fig_gpu1 = plot_filters(weights_gpu1, "Segregated AlexNet - GPU 1 (48 filters)")
    fig_gpu2 = plot_filters(weights_gpu2, "Segregated AlexNet - GPU 2 (48 filters)")
    fig_standard = plot_filters(weights_standard, "Standard AlexNet (96 filters)")

    return fig_gpu1, fig_gpu2, fig_standard

# Load models
parallel_model = AlexNetGPUSimulated()
parallel_model.classifier[-1] = nn.Linear(4096, 10)
parallel_model.load_state_dict(torch.load('alexnet_cifar10.pth'))
parallel_model = parallel_model.to(device)

standard_model = CustomAlexNet()
standard_model.classifier[-1] = nn.Linear(4096, 10)
standard_model.load_state_dict(torch.load('alexnet_custom_cifar10.pth'))
standard_model = standard_model.to(device)

# Visualize filters
fig_gpu1, fig_gpu2, fig_standard = visualize_filters(parallel_model, standard_model)

# Save visualizations
def save_figure(fig, name):
    i = 1
    while os.path.exists(f'{name}_{i}.png'):
        i += 1
    fig.savefig(f'{name}_{i}.png', dpi=300, bbox_inches='tight')
    print(f"Saved {name}_{i}.png")

save_figure(fig_gpu1, 'alexnet_filters_gpu1')
save_figure(fig_gpu2, 'alexnet_filters_gpu2')
save_figure(fig_standard, 'alexnet_filters_standard')

plt.show()

print("Visualizations saved.")