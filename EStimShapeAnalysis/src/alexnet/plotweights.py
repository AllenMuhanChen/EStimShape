import torch
import matplotlib.pyplot as plt
from alexnetparallelgpus import AlexNetGPUSimulated  # Make sure this import matches your file name


def visualize_filters(model, gpu_name):
    # Get the weights of the first convolutional layer
    if gpu_name == 'GPU1':
        weights = model.features_gpu1_1[0].weight.data.cpu()
    else:
        weights = model.features_gpu2_1[0].weight.data.cpu()

    # Normalize the weights for better visualization
    weights = (weights - weights.min()) / (weights.max() - weights.min())

    # Create a grid to place the filter visualizations
    num_filters = weights.shape[0]
    num_rows = 6  # You can adjust this for a different layout
    num_cols = num_filters // num_rows + (1 if num_filters % num_rows != 0 else 0)

    fig, axes = plt.subplots(num_rows, num_cols, figsize=(20, 20))
    fig.suptitle(f'{gpu_name} C1 Filters', fontsize=16)

    for i, ax in enumerate(axes.flat):
        if i < num_filters:
            ax.imshow(weights[i].permute(1, 2, 0))
        ax.axis('off')

    plt.tight_layout()
    return fig


# Load the saved model
model_path = 'data/segregated_6conv_cifar/alexnet_cifar10.pth'  # Update this to your model's path

# Load the state dict
state_dict = torch.load(model_path)

# Create a new model instance
model = AlexNetGPUSimulated()

# Modify the classifier's last layer to match the loaded state dict
num_ftrs = model.classifier[6].in_features
num_classes = state_dict['classifier.6.bias'].size(0)
model.classifier[6] = torch.nn.Linear(num_ftrs, num_classes)

# Load the state dict
model.load_state_dict(state_dict)
model.eval()

# Visualize filters for GPU1
fig1 = visualize_filters(model, 'GPU1')

# Visualize filters for GPU2
fig2 = visualize_filters(model, 'GPU2')

# Save the figures
fig1.savefig('alexnet_c1_filters_gpu1.png', dpi=300, bbox_inches='tight')
fig2.savefig('alexnet_c1_filters_gpu2.png', dpi=300, bbox_inches='tight')

plt.show()

print("Filter visualizations saved as 'alexnet_c1_filters_gpu1.png' and 'alexnet_c1_filters_gpu2.png'")

# Print model output shape
example_input = torch.randn(1, 6, 224, 224)
output = model(example_input)
print(f"Output shape: {output.shape}")