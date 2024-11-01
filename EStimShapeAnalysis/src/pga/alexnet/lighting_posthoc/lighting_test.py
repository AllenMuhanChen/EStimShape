import subprocess
from dataclasses import dataclass
from time import sleep

import numpy as np
from datetime import datetime

from PIL import Image
from clat.util import time_util
from clat.util.connection import Connection
from src.pga.alexnet import alexnet_context
from src.pga.alexnet.onnx_parser import AlexNetONNXResponseParser, UnitIdentifier


def main():
    # Create database connections
    ga_conn = Connection(host='172.30.6.80', user='xper_rw', password='up2nite',
                         database=alexnet_context.ga_database)
    lighting_conn = Connection(host='172.30.6.80', user='xper_rw', password='up2nite',
                               database=alexnet_context.lighting_database)

    # Get top stimuli
    n_stimuli = 10  # Adjust as needed

    top_stims = get_top_n_stimuli(ga_conn, n_stimuli, most_negative=False)

    copy_top_n_to_lighting_db(ga_conn, lighting_conn, top_stims)  # so java code can access original spec info

    ### 3D PORTION
    light_positions = generate_lighting_positions(n_angles=8)

    # Continue with rest of the code...
    write_3d_instructions(lighting_conn, top_stims, light_positions)
    print(f"Written 3D instructions for {len(top_stims)} stimuli with {len(light_positions)} lighting variations")

    # Run the jar file
    jar_path = f"{alexnet_context.allen_dist}/AlexNetLightingPostHocGenerator.jar"
    subprocess.run(["java", "-jar", jar_path], check=True)

    ### 2D PORTION
    query = """
    SELECT sp.path, si.stim_id
    FROM StimPath sp
    JOIN StimInstructions si ON sp.stim_id = si.stim_id
    WHERE si.stim_type = 'TEXTURE_3D_VARIATION'
    """
    lighting_conn.execute(query)
    processed_paths, parent_ids = zip(*lighting_conn.fetch_all())

    write_2d_match_instructions(lighting_conn, processed_paths, parent_ids)
    print("Written 2D match instructions")

    # Run the jar file again
    print("Running jar file again to generate 2D images")
    jar_path = f"{alexnet_context.allen_dist}/AlexNetLightingPostHocGenerator.jar"
    subprocess.run(["java", "-jar", jar_path], check=True)


    ### GETTING DATA VIA ALEXNET
    print("Processing lighting variations through AlexNet")
    unit = alexnet_context.unit
    process_lighting_variations_through_alexnet(lighting_conn, unit)


def process_lighting_variations_through_alexnet(lighting_conn, unit_id: UnitIdentifier):
    """Process all stimuli through AlexNet and save activations to lighting db."""
    # Create parser but only use its process_image functionality
    parser = AlexNetONNXResponseParser(
        lighting_conn,
        "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/data/AlexNetONNX_with_conv3",
        unit_id
    )

    # Get all stim paths from StimInstructions
    query = """
    SELECT si.stim_id, sp.path 
    FROM StimInstructions si
    JOIN StimPath sp ON si.stim_id = sp.stim_id
    """
    lighting_conn.execute(query)
    stims = lighting_conn.fetch_all()

    for stim_id, path in stims:
        # Get activation using existing process_image method
        activation = parser.process_image(path)

        # Store in UnitActivations
        query = """
        INSERT INTO UnitActivations (stim_id, unit, activation) 
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE activation = %s
        """
        lighting_conn.execute(query, (
            stim_id,
            unit_id.to_string(),
            activation,
            activation
        ))
        lighting_conn.mydb.commit()


def copy_top_n_to_lighting_db(ga_conn, lighting_conn, top_stims):
    # Copy stim data for each top stim
    for stim in top_stims:
        parent_id = stim.stim_id

        # Copy parent's StimPath
        ga_conn.execute("SELECT path FROM StimPath WHERE stim_id = %s", (parent_id,))
        path_result = ga_conn.fetch_one()
        if path_result:
            lighting_conn.execute(
                "INSERT INTO StimPath (stim_id, path) VALUES (%s, %s) ON DUPLICATE KEY UPDATE path = VALUES(path)",
                (parent_id, path_result)
            )

        # Copy parent's StimSpec
        ga_conn.execute("SELECT spec FROM StimSpec WHERE id = %s", (parent_id,))
        spec_result = ga_conn.fetch_one()
        if spec_result:
            lighting_conn.execute(
                "INSERT INTO StimSpec (id, spec) VALUES (%s, %s) ON DUPLICATE KEY UPDATE spec = VALUES(spec)",
                (parent_id, spec_result)
            )

        lighting_conn.mydb.commit()


@dataclass
class StimData:
    stim_id: int
    response: float
    path: str
    lineage_id: int


def get_top_n_stimuli(ga_conn, n: int, most_negative=False):
    """Get top N stimuli based on response."""
    query = """
    SELECT s.stim_id, s.response, sp.path, s.lineage_id
    FROM StimGaInfo s
    JOIN StimPath sp ON s.stim_id = sp.stim_id
    WHERE s.response IS NOT NULL
    ORDER BY s.response {} 
    LIMIT %s
    """.format('ASC' if most_negative else 'DESC')

    ga_conn.execute(query, (n,))
    results = ga_conn.fetch_all()
    return [StimData(r[0], r[1], r[2], r[3]) for r in results]


def generate_lighting_positions(n_angles=8):
    """Generate evenly spaced lighting positions on a sphere."""
    angles = np.linspace(0, np.pi, n_angles, endpoint=False)
    radius = 500  # Match the original lighting distance
    w = 1.0

    positions = []
    for theta in angles:
        # Keep light at 45 degrees elevation
        x = radius * np.cos(theta) * np.cos(np.pi / 4)
        y = radius * np.sin(theta) * np.cos(np.pi / 4)
        z = radius * np.sin(np.pi / 4)
        positions.append([x, y, z, w])

    return positions


def write_3d_instructions(lighting_conn, stimuli, light_positions):
    """Write instructions for 3D texture variations."""
    for stim in stimuli:
        for texture in ['SPECULAR', 'SHADE']:
            for light_pos in light_positions:
                stim_id = time_util.now()
                sleep(.001)

                query = """
                INSERT INTO StimInstructions 
                (stim_id, parent_id, stim_type, texture_type, 
                 light_pos_x, light_pos_y, light_pos_z, light_pos_w, contrast)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                params = (
                    stim_id,
                    stim.stim_id,
                    'TEXTURE_3D_VARIATION',
                    texture,
                    light_pos[0], light_pos[1], light_pos[2], light_pos[3],
                    1.0
                )

                lighting_conn.execute(query, params)
                lighting_conn.mydb.commit()


def calculate_average_luminance(image_path):
    """Calculate average luminance of an image, excluding gray background (127/128 RGB)."""
    img = Image.open(image_path).convert('RGB')
    img_array = np.array(img)

    # Create mask to exclude pixels that are exactly background gray (both 127 and 128)
    background_mask = ((img_array[:, :, 0] == 127) & (img_array[:, :, 1] == 127) & (img_array[:, :, 2] == 127)) | \
                      ((img_array[:, :, 0] == 128) & (img_array[:, :, 1] == 128) & (img_array[:, :, 2] == 128))
    foreground_mask = ~background_mask

    # Get only foreground pixels
    foreground_pixels = img_array[foreground_mask]

    if len(foreground_pixels) == 0:
        return 0.0

    # Calculate luminance only for foreground pixels
    # Calculate average pixel color:
    average = np.mean(foreground_pixels, axis=0)
    # calculate average brightness
    luminance = (0.2126 * foreground_pixels[:, 0] +
                 0.7152 * foreground_pixels[:, 1] +
                 0.0722 * foreground_pixels[:, 2])

    return max(average) / 255.0  # Normalize to 0-1


def write_2d_match_instructions(lighting_conn, processed_3d_paths, parent_ids):
    """Write instructions for 2D matches based on processed 3D images."""
    for path, parent_id in zip(processed_3d_paths, parent_ids):
        luminance = calculate_average_luminance(path)
        stim_id = time_util.now()
        sleep(.001)

        query = """
        INSERT INTO StimInstructions 
        (stim_id, parent_id, stim_type, texture_type, 
         light_pos_x, light_pos_y, light_pos_z, light_pos_w, contrast)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            stim_id,
            parent_id,
            '2D_MATCH',
            '2D',
            0, 0, 0, 0,  # Light position not used for 2D
            luminance  # Use average luminance as contrast
        )

        lighting_conn.execute(query, params)
        lighting_conn.mydb.commit()


if __name__ == "__main__":
    main()
