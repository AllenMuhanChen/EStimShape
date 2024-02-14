import pandas as pd
import xmltodict

from clat.compile.task.base_database_fields import TaskIdField, StimSpecIdField, StimSpecField
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.compile.task.task_field import TaskFieldList
from clat.intan.channels import Channel
from clat.util.connection import Connection

import torchvision.transforms as transforms
from torchvision import models
from PIL import Image




def main():
    # PARAMETERS
    conn = Connection("allen_estimshape_ga_dev_240207")
    unit = 12
    loc_x = 7
    loc_y = 7

    fields = TaskFieldList()
    fields.append(TaskIdField(name="TaskId"))
    fields.append(StimSpecIdField(conn=conn, name="StimId"))
    fields.append(StimSpecField(conn=conn, name="StimSpec"))
    fields.append(StimPathField(conn=conn, name="StimPath"))

    data = fields.to_data(collect_task_ids(conn))
    paths = list(data["StimPath"])
    activations = extract_activations(paths)

    unit_activations = [activation[0, unit, loc_x, loc_y].item() for activation in activations]

    insert_to_channel_responses(conn, unit_activations, data)


def insert_to_channel_responses(conn, response_rates: list, data: pd.DataFrame):
    for (stim_id, task_id), response_rate in zip(data[["StimId", "TaskId"]].values, response_rates):
        query = ("INSERT IGNORE INTO ChannelResponses "
                 "(stim_id, task_id, channel, spikes_per_second) "
                 "VALUES (%s, %s, %s, %s)")
        params = (int(stim_id), int(task_id), Channel.D_003.value, float(response_rate))
        conn.execute(query, params)
        conn.mydb.commit()


def extract_activations(paths):
    # Load the pre-trained AlexNet model
    alexnet = models.alexnet(pretrained=True)
    alexnet.eval()  # Set model to evaluation mode

    # Load and preprocess images
    images = [load_and_preprocess_image(path) for path in paths]

    # Get activations
    activations = get_activations_from_layer3(alexnet, images)

    return activations


def collect_task_ids(conn):
    task_id_collector = TaskIdCollector(conn)
    task_ids = task_id_collector.collect_task_ids()
    return task_ids


# Function to load an image and preprocess it
def load_and_preprocess_image(image_path):
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    image = Image.open(image_path).convert('RGB')
    image = preprocess(image)
    # Add a batch dimension
    image = image.unsqueeze(0)
    return image


# Function to extract activations
def get_activations_from_layer3(model, images):
    activations = []

    # Register hook to capture the activations
    def hook(module, input, output):
        activations.append(output)

    handle = model.features[6].register_forward_hook(hook)  # Layer 3 is the 7th layer in features

    # Pass images through the model
    for image in images:
        model(image)

    # Remove the hook
    handle.remove()

    return activations


# Main function


class StimPathField(StimSpecField):
    def __init__(self, conn: Connection, name: str = "StimPath"):
        super().__init__(conn, name)

    def get(self, task_id: int) -> str:
        # Execute the query to get the StimPath based on task_id
        # Note: Replace the query with the appropriate one for your schema
        stim_spec = super().get(task_id)
        stim_spec_dict = xmltodict.parse(stim_spec)
        stim_path = stim_spec_dict["StimSpec"]['path']
        return stim_path


if __name__ == "__main__":
    main()
