import os
import torch
import matplotlib.pyplot as plt
from collections import defaultdict
import numpy as np


def extract_data_from_checkpoint(checkpoint_path):
    checkpoint = torch.load(checkpoint_path, map_location=torch.device('cpu'))
    scheduler_state = checkpoint['scheduler_state_dict']

    # Extract learning rate
    if 'last_lr' in scheduler_state:
        lr = scheduler_state['last_lr'][0]
    elif '_last_lr' in scheduler_state:
        lr = scheduler_state['_last_lr'][0]
    else:
        lr = checkpoint['optimizer_state_dict']['param_groups'][0]['lr']

    # Extract accuracies
    train_acc = checkpoint['train_acc']
    val_acc = checkpoint['val_acc']

    # Extract model state dict
    model_state = checkpoint['model_state_dict']

    return lr, train_acc, val_acc, model_state


def calculate_weight_change(prev_state, curr_state, prev_lr):
    changes = {}
    for key in curr_state.keys():
        if 'weight' in key:
            prev_weight = prev_state[key].cpu().numpy()
            curr_weight = curr_state[key].cpu().numpy()
            normalized_change = np.linalg.norm(curr_weight - prev_weight) / np.sqrt(np.prod(curr_weight.shape))
            normalized_change = normalized_change / prev_lr
            changes[key] = normalized_change
    return changes


def analyze_checkpoints(checkpoint_dir):
    data_history = defaultdict(lambda: {'lr': 0, 'train_acc': 0, 'val_acc': 0, 'weight_changes': {}})
    prev_state = None
    prev_lr = None

    # Get all checkpoint files and sort them by epoch number
    checkpoint_files = []
    for filename in os.listdir(checkpoint_dir):
        if filename.startswith('checkpoint_epoch_') and filename.endswith('.pth'):
            epoch = int(filename.split('_')[-1].split('.')[0])
            checkpoint_files.append((epoch, filename))

    # Sort by epoch number
    checkpoint_files.sort(key=lambda x: x[0])

    for epoch, filename in checkpoint_files:
        print(f"Processing {filename}")
        filepath = os.path.join(checkpoint_dir, filename)
        lr, train_acc, val_acc, model_state = extract_data_from_checkpoint(filepath)

        weight_changes = {}
        if prev_state is not None and prev_lr is not None:
            weight_changes = calculate_weight_change(prev_state, model_state, prev_lr)

        data_history[epoch] = {
            'lr': lr,
            'train_acc': train_acc,
            'val_acc': val_acc,
            'weight_changes': weight_changes
        }

        prev_state = model_state
        prev_lr = lr

    return data_history


def plot_history(data_history):
    epochs = sorted(data_history.keys())
    lrs = [data_history[epoch]['lr'] for epoch in epochs]
    train_accs = [data_history[epoch]['train_acc'] * 100 for epoch in epochs]
    val_accs = [data_history[epoch]['val_acc'] * 100 for epoch in epochs]

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 15), sharex=True)

    # Plot learning rate
    ax1.plot(epochs, lrs, marker='o', color='b')
    ax1.set_ylabel('Learning Rate')
    ax1.set_yscale('log')
    ax1.set_title('Learning Rate vs Epoch')
    ax1.grid(True)

    # Plot accuracies
    ax2.plot(epochs, train_accs, marker='o', color='g', label='Train Accuracy')
    ax2.plot(epochs, val_accs, marker='o', color='r', label='Validation Accuracy')
    ax2.set_ylabel('Accuracy (%)')
    ax2.set_title('Train and Validation Accuracy vs Epoch')
    ax2.legend()
    ax2.grid(True)

    # Plot weight changes
    layer_changes = defaultdict(list)
    for epoch in epochs[1:]:  # Skip first epoch as it has no changes
        changes = data_history[epoch]['weight_changes']
        for layer, change in changes.items():
            layer_changes[layer].append(change)

    label_map = {
        'features_gpu1_1.0.weight': 'C1_1',
        'features_gpu1_1.4.weight': 'C2_1',
        'features_gpu2_1.0.weight': 'C1_2',
        'features_gpu2_1.4.weight': 'C2_2',
        'features_shared.0.weight': 'C3',
        'features_gpu1_2.0.weight': 'C4_1',
        'features_gpu1_2.2.weight': 'C5_1',
        'features_gpu2_2.0.weight': 'C4_2',
        'features_gpu2_2.2.weight': 'C5_2',
        'classifier.1.weight': 'FC1',
        'classifier.4.weight': 'FC2',
        'classifier.6.weight': 'FC3'
    }

    color_map = {
        'C1_1': '#FF6666',  # Light Red
        'C1_2': '#CC0000',  # Dark Red
        'C2_1': '#66FF66',  # Light Green
        'C2_2': '#00CC00',  # Dark Green
        'C3': '#3366FF',  # Blue
        'C4_1': '#FF66FF',  # Light Magenta
        'C4_2': '#CC00CC',  # Dark Magenta
        'C5_1': '#FFFF66',  # Light Yellow
        'C5_2': '#CCCC00',  # Dark Yellow
        'FC1': '#FF9900',  # Orange
        'FC2': '#996633',  # Brown
        'FC3': '#666666'  # Gray
    }

    for layer, changes in layer_changes.items():
        label = label_map.get(layer)
        color = color_map.get(label)
        ax3.plot(epochs[1:], changes, label=label, color=color)

    ax3.set_xlabel('Epoch')
    ax3.set_ylabel('Weight Change (Euclidean distance)')
    ax3.set_title('Layer Weight Changes vs Epoch')
    ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax3.grid(True)

    plt.tight_layout()
    plt.savefig('training_history_with_weight_changes.png', bbox_inches='tight')
    plt.close()


def main():
    checkpoint_dir = '/home/connorlab/PycharmProjects/EStimShape/EStimShapeAnalysis/src/alexnet'
    data_history = analyze_checkpoints(checkpoint_dir)
    plot_history(data_history)
    print(f"Training history plot saved as 'training_history_with_weight_changes.png'")


if __name__ == "__main__":
    main()