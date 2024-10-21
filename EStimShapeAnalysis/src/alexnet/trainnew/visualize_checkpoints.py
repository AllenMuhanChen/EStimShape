import torch
import matplotlib.pyplot as plt
from alexnetparallelgpus import AlexNetGPUSimulated
import os


def load_checkpoint(checkpoint_path):
    checkpoint = torch.load(checkpoint_path, map_location=torch.device('cpu'))
    model = AlexNetGPUSimulated()
    model.load_state_dict(checkpoint['model_state_dict'])
    return model, checkpoint['epoch']


def visualize_filters(model, epoch):
    weights_gpu1 = model.features_gpu1_1[0].weight.data.cpu()
    weights_gpu2 = model.features_gpu2_1[0].weight.data.cpu()

    # Normalize weights
    def normalize(w):
        return (w - w.min()) / (w.max() - w.min())

    weights_gpu1 = normalize(weights_gpu1)
    weights_gpu2 = normalize(weights_gpu2)

    def plot_filters(weights, title):
        num_filters = weights.shape[0]
        num_rows, num_cols = 6, 8  # For 48 filters

        fig, axes = plt.subplots(num_rows, num_cols, figsize=(20, 15))
        fig.suptitle(title, fontsize=16)

        for i in range(num_filters):
            row = i // num_cols
            col = i % num_cols
            axes[row, col].imshow(weights[i].permute(1, 2, 0))
            axes[row, col].axis('off')

        plt.tight_layout()
        return fig

    fig_gpu1 = plot_filters(weights_gpu1, f"AlexNet ImageNet - GPU 1 (Epoch {epoch})")
    fig_gpu2 = plot_filters(weights_gpu2, f"AlexNet ImageNet - GPU 2 (Epoch {epoch})")

    return fig_gpu1, fig_gpu2


def save_figure(fig, folder, name):
    if not os.path.exists(folder):
        os.makedirs(folder)
    filepath = os.path.join(folder, f'{name}.png')
    fig.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"Saved {filepath}")


def visualization_exists(folder, name):
    return os.path.exists(os.path.join(folder, f'{name}.png'))


# Create a new folder for visualizations
visualization_folder = 'imagenet_visualizations'
if not os.path.exists(visualization_folder):
    os.makedirs(visualization_folder)

# Find all checkpoint files
checkpoint_files = sorted([f for f in os.listdir('.') if f.startswith('checkpoint_epoch_')],
                          key=lambda x: int(x.split('_')[-1].split('.')[0]))

# Visualize weights for each checkpoint
for checkpoint_file in checkpoint_files:
    epoch = int(checkpoint_file.split('_')[-1].split('.')[0])

    # Check if visualizations for this epoch already exist
    if (visualization_exists(visualization_folder, f'alexnet_imagenet_filters_gpu1_epoch_{epoch}') and
            visualization_exists(visualization_folder, f'alexnet_imagenet_filters_gpu2_epoch_{epoch}')):
        print(f"Visualizations for epoch {epoch} already exist. Skipping.")
        continue

    model, _ = load_checkpoint(checkpoint_file)
    fig_gpu1, fig_gpu2 = visualize_filters(model, epoch)

    save_figure(fig_gpu1, visualization_folder, f'alexnet_imagenet_filters_gpu1_epoch_{epoch}')
    save_figure(fig_gpu2, visualization_folder, f'alexnet_imagenet_filters_gpu2_epoch_{epoch}')

    plt.close(fig_gpu1)
    plt.close(fig_gpu2)

print(f"Visualizations saved for all checkpoints in the '{visualization_folder}' folder.")