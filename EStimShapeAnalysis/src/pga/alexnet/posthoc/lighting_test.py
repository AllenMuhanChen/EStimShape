from dataclasses import dataclass
from time import sleep

import numpy as np
from datetime import datetime

from PIL import Image
from clat.util import time_util
from clat.util.connection import Connection
from src.pga.alexnet import alexnet_context


def main():
    # Create database connections
    ga_conn = Connection(host='172.30.6.80', user='xper_rw', password='up2nite',
                         database=alexnet_context.ga_database)
    lighting_conn = Connection(host='172.30.6.80', user='xper_rw', password='up2nite',
                               database=alexnet_context.lighting_database)

    # Get top stimuli
    n_stimuli = 10  # Adjust as needed
    top_stims = get_top_n_stimuli(ga_conn, n_stimuli, most_negative=False)

    # Generate lighting positions
    light_positions = generate_lighting_positions(n_angles=8)

    # Write 3D variation instructions
    write_3d_instructions(lighting_conn, top_stims, light_positions)
    print(f"Written 3D instructions for {len(top_stims)} stimuli with {len(light_positions)} lighting variations")

    # At this point, Java needs to process these instructions and generate the images
    input("Press Enter after Java has processed all 3D variations...")

    # Get the paths of the processed 3D images
    query = """
    SELECT sp.path, si.parent_id
    FROM StimPath sp
    JOIN StimInstructions si ON sp.stim_id = si.stim_id
    WHERE si.stim_type = 'TEXTURE_3D_VARIATION'
    """
    lighting_conn.execute(query)
    processed_paths, parent_ids = zip(*lighting_conn.fetch_all())

    # Write 2D match instructions based on processed 3D images
    write_2d_match_instructions(lighting_conn, processed_paths, parent_ids)
    print("Written 2D match instructions")


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
                 light_pos_x, light_pos_y, light_pos_z, light_pos_w)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """

                params = (
                    stim_id,
                    stim.stim_id,
                    'TEXTURE_3D_VARIATION',
                    texture,
                    light_pos[0], light_pos[1], light_pos[2], light_pos[3]
                )

                lighting_conn.execute(query, params)
                lighting_conn.mydb.commit()


def calculate_average_luminance(image_path):
    """Calculate average luminance of an image."""
    img = Image.open(image_path).convert('RGB')
    img_array = np.array(img)

    # Convert RGB to luminance using standard coefficients
    luminance = 0.2126 * img_array[:, :, 0] + 0.7152 * img_array[:, :, 1] + 0.0722 * img_array[:, :, 2]
    return np.mean(luminance) / 255.0  # Normalize to 0-1


def write_2d_match_instructions(lighting_conn, processed_3d_paths, parent_ids):
    """Write instructions for 2D matches based on processed 3D images."""
    for path, parent_id in zip(processed_3d_paths, parent_ids):
        luminance = calculate_average_luminance(path)
        stim_id = int(datetime.now().strftime("%Y%m%d%H%M%S%f"))

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
