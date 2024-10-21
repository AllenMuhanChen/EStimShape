import torch
import torch.nn as nn
import torch.nn.init as init

class AlexNetGPUSimulated(nn.Module):
    def __init__(self):
        super(AlexNetGPUSimulated, self).__init__()

        # GPU 1 Pre-Shared Layer
        self.features_gpu1_1 = nn.Sequential(
            nn.Conv2d(3, 48, kernel_size=11, stride=4, padding=2),
            nn.ReLU(inplace=True),
            nn.LocalResponseNorm(size=5, alpha=0.0001, beta=0.75, k=2),  # section 3.3
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(48, 128, kernel_size=5, padding=2),
            nn.ReLU(inplace=True),
            nn.LocalResponseNorm(size=5, alpha=0.0001, beta=0.75, k=2),  # section 3.3
            nn.MaxPool2d(kernel_size=3, stride=2)
        )
        # GPU 2 Pre-Shared Layer
        self.features_gpu2_1 = nn.Sequential(
            nn.Conv2d(3, 48, kernel_size=11, stride=4, padding=2),
            nn.ReLU(inplace=True),
            nn.LocalResponseNorm(size=5, alpha=0.0001, beta=0.75, k=2),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(48, 128, kernel_size=5, padding=2),
            nn.ReLU(inplace=True),
            nn.LocalResponseNorm(size=5, alpha=0.0001, beta=0.75, k=2),  # section 3.3
            nn.MaxPool2d(kernel_size=3, stride=2)
        )

        # Shared layer (connection point)
        self.features_shared = nn.Sequential(
            nn.Conv2d(256, 384, kernel_size=3, padding=1),
            nn.ReLU(inplace=True)
        )

        # GPU 1 Post-Shared Layer
        self.features_gpu1_2 = nn.Sequential(
            nn.Conv2d(192, 192, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(192, 128, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2)
        )

        # GPU 2 Post-Shared Layer
        self.features_gpu2_2 = nn.Sequential(
            nn.Conv2d(192, 192, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(192, 128, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2)
        )

        # Classifier (fully connected layers)
        self.classifier = nn.Sequential(
            nn.Dropout(),
            nn.Linear(256 * 6 * 6, 4096),
            nn.ReLU(inplace=True),
            nn.Dropout(),
            nn.Linear(4096, 4096),
            nn.ReLU(inplace=True),
            nn.Linear(4096, 1000)
        )

        # self._initialize_weights()

    def _initialize_weights(self):
        conv_layer_count = 0
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                conv_layer_count += 1
                init.normal_(m.weight, mean=0, std=0.01)
                if m.bias is not None:
                    if conv_layer_count in [2, 4, 5]:
                        init.constant_(m.bias, 1)
                    else:
                        init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                init.normal_(m.weight, mean=0, std=0.01)
                if m.bias is not None:
                    if m in [self.classifier[1], self.classifier[4]]:  # Hidden layers
                        init.constant_(m.bias, 1)
                    else:
                        init.constant_(m.bias, 0)

    def forward(self, x):
        # Split input for GPU simulation
        # x1, x2 = torch.split(x, [3, 3], dim=1)
        # Process through initial GPU-specific layers
        x1 = self.features_gpu1_1(x)
        x2 = self.features_gpu2_1(x)

        # Concatenate for shared layer (connection point)
        x = torch.cat((x1, x2), 1)
        x = self.features_shared(x)

        # Split again for GPU-specific processing
        x1, x2 = torch.split(x, [192, 192], dim=1)

        # Continue GPU-specific processing
        x1 = self.features_gpu1_2(x1)
        x2 = self.features_gpu2_2(x2)

        # Final concatenation
        x = torch.cat((x1, x2), 1)

        # Flatten the output for the classifier
        x = x.view(x.size(0), 256 * 6 * 6)

        # Classifier (fully connected layers)
        x = self.classifier(x)

        return x

# Instantiate the model
model = AlexNetGPUSimulated()

# Print model summary
print(model)
