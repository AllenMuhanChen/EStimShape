import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models, datasets, transforms
from torch.utils.data import DataLoader
from tqdm import tqdm
import matplotlib.pyplot as plt
from alexnetparallelgpus import AlexNetGPUSimulated
import os

# Set device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Hyperparameters
batch_size = 128
num_epochs = 50
learning_rate = 0.01
momentum = 0.9
weight_decay = 0.0005

# Data transformations
transform = transforms.Compose([
    transforms.Resize(224),
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])

# Load CIFAR-10 dataset
train_dataset = datasets.CIFAR10(root='./data', train=True, download=True, transform=transform)
test_dataset = datasets.CIFAR10(root='./data', train=False, download=True, transform=transform)

train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=2)
test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=2)


def train_model(model, loader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for inputs, targets in tqdm(loader, desc="Training"):
        inputs, targets = inputs.to(device), targets.to(device)

        if isinstance(model, AlexNetGPUSimulated):
            inputs = torch.cat([inputs, inputs], dim=1)

        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        _, predicted = outputs.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()

    epoch_loss = running_loss / len(loader)
    epoch_acc = correct / total
    return epoch_loss, epoch_acc


def validate_model(model, loader, criterion, device):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for inputs, targets in tqdm(loader, desc="Validating"):
            inputs, targets = inputs.to(device), targets.to(device)

            if isinstance(model, AlexNetGPUSimulated):
                inputs = torch.cat([inputs, inputs], dim=1)

            outputs = model(inputs)
            loss = criterion(outputs, targets)

            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

    epoch_loss = running_loss / len(loader)
    epoch_acc = correct / total
    return epoch_loss, epoch_acc


# Create and train standard AlexNet
standard_model = models.alexnet(pretrained=False)
standard_model.classifier[-1] = nn.Linear(4096, 10)
standard_model = standard_model.to(device)

criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(standard_model.parameters(), lr=learning_rate, momentum=momentum, weight_decay=weight_decay)
scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=30, gamma=0.1)

# Check if the standard model has already been trained
if not os.path.exists('alexnet_standard_cifar10.pth'):
    print("Training Standard AlexNet on CIFAR-10")
    for epoch in range(num_epochs):
        print(f"Epoch {epoch + 1}/{num_epochs}")
        train_loss, train_acc = train_model(standard_model, train_loader, criterion, optimizer, device)
        test_loss, test_acc = validate_model(standard_model, test_loader, criterion, device)
        print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}")
        print(f"Test Loss: {test_loss:.4f}, Test Acc: {test_acc:.4f}")
        scheduler.step()

    torch.save(standard_model.state_dict(), 'alexnet_standard_cifar10.pth')
    print("Standard AlexNet training completed. Model saved as 'alexnet_standard_cifar10.pth'")
else:
    print("Loading pre-trained Standard AlexNet")
    standard_model.load_state_dict(torch.load('alexnet_standard_cifar10.pth'))

