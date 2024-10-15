import sys

import torch
import torch.nn as nn
import torch.optim as optim
from torch import autocast
from torch.cuda.amp import GradScaler
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader, Dataset, ConcatDataset
from torchvision import transforms, datasets
from PIL import Image
import os
from tqdm import tqdm

from coloraugment.coloraugment import PCAAugmentation
from alexnetparallelgpus import AlexNetGPUSimulated

# Set up paths
imagenet_path = '/home/connorlab/imagenet/imagenet-object-localization-challenge/ILSVRC/Data/CLS-LOC/'
train_dir = os.path.join(imagenet_path, 'train')
val_dir = os.path.join(imagenet_path, 'val')
val_label_file = "/home/connorlab/imagenet/imagenet-object-localization-challenge/LOC_val_solution.csv"

try:
    batch_size = int(sys.argv[1])
    num_workers = int(sys.argv[2])
    prefetch_factor = int(sys.argv[3])
except IndexError as ie:
    batch_size = 128
    num_workers = 12
    prefetch_factor = None


# Custom dataset for validation set
class ImageNetValidation(Dataset):
    def __init__(self, val_dir, label_file, transform=None):
        self.val_dir = val_dir
        self.transform = transform
        self.img_labels = {}

        # Get the mapping of WordNet IDs to indices from the training set
        train_dataset = datasets.ImageFolder(train_dir)
        self.class_to_idx = train_dataset.class_to_idx

        # Read validation labels
        with open(label_file, 'r') as f:
            next(f)  # Skip header
            for line in f:
                img_name, label = line.strip().split(',')
                wordnet_id = label.split()[0]  # Extract WordNet ID
                if wordnet_id in self.class_to_idx:
                    self.img_labels[img_name] = self.class_to_idx[wordnet_id]
                else:
                    print(f"Warning: {wordnet_id} not found in training classes")

        self.images = list(self.img_labels.keys())

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_name = self.images[idx]
        img_path = os.path.join(self.val_dir, img_name + '.JPEG')  # Add .JPEG extension
        image = Image.open(img_path).convert('RGB')
        label = self.img_labels[img_name]

        if self.transform:
            image = self.transform(image)

        return image, label


# Data augmentation and normalization
train_transform = transforms.Compose([
    transforms.RandomResizedCrop(227),
    transforms.RandomHorizontalFlip(),
    PCAAugmentation(alphastd=0.1),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

val_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(227),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Create datasets
train_dataset = datasets.ImageFolder(train_dir, transform=train_transform)
val_dataset = ImageNetValidation(val_dir, val_label_file, transform=val_transform)

# DataLoaders
# batch_size = 256
train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=True, prefetch_factor=prefetch_factor)
val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True, prefetch_factor=prefetch_factor)

# Initialize model, loss function, and optimizer
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = AlexNetGPUSimulated()
model = model.to(device)

criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(model.parameters(), lr=batch_size / 128 * .01, momentum=0.9, weight_decay=5e-4)
scheduler = ReduceLROnPlateau(optimizer, mode='min', factor=0.1, patience=5, verbose=True)  # Section 5
scaler = GradScaler()


# Checkpointing functions
def save_checkpoint(epoch, model, optimizer, scheduler, scaler, train_loss, train_acc, val_loss, val_acc):
    checkpoint = {
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'scheduler_state_dict': scheduler.state_dict(),
        'scaler_state_dict': scaler.state_dict(),
        'train_loss': train_loss,
        'train_acc': train_acc,
        'val_loss': val_loss,
        'val_acc': val_acc
    }
    torch.save(checkpoint, f'checkpoint_epoch_{epoch}.pth')
    print(f"Checkpoint saved for epoch {epoch}")


def load_checkpoint(checkpoint_path):
    checkpoint = torch.load(checkpoint_path)
    model.load_state_dict(checkpoint['model_state_dict'])
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
    scaler.load_state_dict(checkpoint['scaler_state_dict'])
    return checkpoint['epoch'], checkpoint['train_loss'], checkpoint['train_acc'], checkpoint['val_loss'], checkpoint[
        'val_acc']


# Training function with mixed precision
def train_one_epoch(model, loader, criterion, optimizer, device, scaler):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for inputs, targets in tqdm(loader, desc="Training"):
        inputs, targets = inputs.to(device, non_blocking=True), targets.to(device, non_blocking=True)

        optimizer.zero_grad()

        # Runs the forward pass with autocasting
        with autocast(device.type):
            outputs = model(inputs)
            loss = criterion(outputs, targets)

        # Scales loss and calls backward()
        scaler.scale(loss).backward()

        # Unscales gradients and calls optimizer.step()
        scaler.step(optimizer)

        # Updates the scale for next iteration
        scaler.update()

        running_loss += loss.item()
        _, predicted = outputs.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()

    epoch_loss = running_loss / len(loader)
    epoch_acc = correct / total
    return epoch_loss, epoch_acc


# Validation function
def validate(model, loader, criterion, device):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for inputs, targets in tqdm(loader, desc="Validating"):
            # inputs = torch.cat([inputs, inputs], dim=1)  # Duplicate channels for our 6-channel input
            inputs, targets = inputs.to(device), targets.to(device)

            outputs = model(inputs)
            loss = criterion(outputs, targets)

            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

    epoch_loss = running_loss / len(loader)
    epoch_acc = correct / total
    return epoch_loss, epoch_acc


def main():
    # Training loop with checkpointing
    num_epochs = 90
    start_epoch = 0
    checkpoint_interval = 1  # Save a checkpoint every epoch
    # Check if a checkpoint exists
    checkpoint_files = [f for f in os.listdir('.') if f.startswith('checkpoint_epoch_')]
    if checkpoint_files:
        latest_checkpoint = max(checkpoint_files, key=lambda x: int(x.split('_')[-1].split('.')[0]))
        print(f"Resuming from checkpoint: {latest_checkpoint}")
        start_epoch, train_loss, train_acc, val_loss, val_acc = load_checkpoint(latest_checkpoint)
        start_epoch += 1  # Start from the next epoch
        print(f"Resuming from epoch {start_epoch}")
    for epoch in range(start_epoch, num_epochs):
        print(f"Epoch {epoch}/{num_epochs}")

        train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer, device, scaler)
        val_loss, val_acc = validate(model, val_loader, criterion, device)

        print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}")
        print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}")

        scheduler.step(val_loss)

        # Save checkpoint
        if (epoch) % checkpoint_interval == 0:
            save_checkpoint(epoch, model, optimizer, scheduler, scaler, train_loss, train_acc, val_loss, val_acc)
    # Save the final trained model
    torch.save(model.state_dict(), 'alexnet_imagenet_final.pth')
    print("Training completed. Final model saved as 'alexnet_imagenet_final.pth'")
    # Print dataset sizes
    print(f"Original training dataset size: {len(train_dataset)}")
    print(f"Augmented training dataset size: {len(train_dataset)}")
    print(f"Validation dataset size: {len(val_dataset)}")


if __name__ == "__main__":
    print(sys.argv)
    main()
