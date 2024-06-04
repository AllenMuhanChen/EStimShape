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

from src.startup import config


def main():
    # run_full_auto()
    run_training()

def run_training():
    conn = config.ga_config.connection()

    channel_numbers_top_to_bottom = [15, 16, 1, 30, 8, 23, 0, 31, 14, 17, 2, 29, 13, 18, 7, 24, 3, 28, 12, 19, 4, 27, 9,
                                     22, 11, 20, 5, 26, 10, 21, 6, 25]
    channel_strings_top_to_bottom = [f"A-{num:03}" for num in channel_numbers_top_to_bottom]

    units = [70, 71, 117, 30, 36, 22, 28, 10]
    loc_xs = [6, 7]
    loc_ys = [6, 7]



    # Prepare task fields
    fields = TaskFieldList()
    fields.append(TaskIdField(name="TaskId"))
    fields.append(StimSpecIdField(conn=conn, name="StimId"))
    fields.append(StimSpecField(conn=conn, name="StimSpec"))
    fields.append(StimPathField(conn=conn, name="StimPath"))
    ids = collect_task_ids(conn)
    data = fields.to_data(ids)
    existing_task_ids = fetch_existing_task_ids(conn)
    data = data[~data['TaskId'].isin(existing_task_ids)]  # Filter out existing task IDs
    data = data[data["StimPath"] != "None"]

    data = data[data["StimPath"] != "catch"]
    catch_data = data[data["StimPath"] == "catch"]


    paths = list(data["StimPath"])

    # print how many paths
    print("Processing " + str(len(paths)) + " Paths")
    # Extract activations
    activations = extract_activations(paths)

    # Process regular data
    channel_index = 0
    for unit in units:
        for loc_x in loc_xs:
            for loc_y in loc_ys:
                # Compute unit activation for each channel configuration
                unit_activations = [activation[0, unit, loc_x, loc_y].item() for activation in activations]

                # Get the current channel string
                channel = channel_strings_top_to_bottom[channel_index]

                # Insert activations into the database
                insert_to_channel_responses(conn, unit_activations, data, channel)

                # Update the channel index for the next iteration
                channel_index += 1

    # Process catch trials
    default_activation = 0
    channel_index = 0
    for unit in units:
        for loc_x in loc_xs:
            for loc_y in loc_ys:
                # Get the current channel string
                channel = channel_strings_top_to_bottom[channel_index]

                # Prepare a default activation response for each channel
                insert_to_channel_responses(conn, [default_activation] * len(activations), catch_data, channel)

                # Update the channel index for the next iteration
                channel_index += 1

def fetch_existing_task_ids(conn):
    """
    Fetch task IDs that already have entries in the ChannelResponses table.
    """
    query = "SELECT DISTINCT task_id FROM ChannelResponses"

    conn.execute(query)
    # Fetch all distinct task IDs already present in ChannelResponses
    existing_task_ids = {row[0] for row in conn.fetch_all()}
    return existing_task_ids

def run_full_auto_mock():
    # PARAMETERS
    conn = Connection("allen_estimshape_ga_dev_240207")
    # unit = 12 #check 7 next, which would 60 max resp from Mohammad
    unit = 70
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

def insert_to_channel_responses(conn, response_rates: list, data: pd.DataFrame, channel: str):
    for (stim_id, task_id), response_rate in zip(data[["StimId", "TaskId"]].values, response_rates):
        query = ("INSERT IGNORE INTO ChannelResponses "
                 "(stim_id, task_id, channel, spikes_per_second) "
                 "VALUES (%s, %s, %s, %s)")
        params = (int(stim_id), int(task_id), channel, float(response_rate))
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
        stim_spec = super().get(task_id)
        stim_spec_dict = xmltodict.parse(stim_spec)

        # Extract the path
        stim_path = stim_spec_dict["StimSpec"]['path']

        # Check if the path contains the 'sftp:host' segment and adjust if necessary
        if 'sftp:host=' in stim_path:
            # Cut from '/home/' found after 'sftp:host=IP'
            home_index = stim_path.find('/home/')
            if home_index != -1:
                stim_path = stim_path[home_index:]

        return stim_path

if __name__ == "__main__":
    main()
