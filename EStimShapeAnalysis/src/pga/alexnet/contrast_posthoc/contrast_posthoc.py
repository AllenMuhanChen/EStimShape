import subprocess
from dataclasses import dataclass
from time import sleep

import numpy as np
from datetime import datetime

from PIL import Image
from clat.util import time_util
from clat.util.connection import Connection
from src.pga.alexnet import alexnet_context
from src.pga.alexnet.onnx_parser import AlexNetONNXResponseParser


def main():
    # Create database connections
    ga_conn = Connection(host='172.30.6.80', user='xper_rw', password='up2nite',
                       database=alexnet_context.ga_database)
    contrast_conn = Connection(host='172.30.6.80', user='xper_rw', password='up2nite',
                           database=alexnet_context.contrast_database)

    # Get top stimuli
    n_stimuli = 10  # Adjust as needed
    top_stims = get_top_n_stimuli(ga_conn, n_stimuli, most_negative=False)

    # Copy stimulus data to contrast db
    copy_top_n_to_contrast_db(ga_conn, contrast_conn, top_stims)

    # Generate contrasts between 0.2 and 1.0
    contrasts = np.linspace(0.2, 1.0, 9)  # 9 contrast levels

    # Write instructions for both 3D and 2D variations
    write_3d_instructions(contrast_conn, top_stims, contrasts)
    print(f"Written 3D instructions for {len(top_stims)} stimuli with {len(contrasts)} contrast variations")

    # Run the jar file to generate 3D images
    jar_path = f"{alexnet_context.allen_dist}/AlexNetContrastPostHocGenerator.jar"
    subprocess.run(["java", "-jar", jar_path], check=True)

    # Write 2D match instructions
    write_2d_match_instructions(contrast_conn, top_stims, contrasts)
    print("Written 2D match instructions")

    # Run the jar file again for 2D images
    subprocess.run(["java", "-jar", jar_path], check=True)

    # Process through AlexNet
    print("Processing contrast variations through AlexNet")
    unit = alexnet_context.unit
    process_contrast_variations_through_alexnet(contrast_conn, unit)


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


def copy_top_n_to_contrast_db(ga_conn, contrast_conn, top_stims):
    # Copy stim data for each top stim
    for stim in top_stims:
        parent_id = stim.stim_id

        # Copy parent's StimPath
        ga_conn.execute("SELECT path FROM StimPath WHERE stim_id = %s", (parent_id,))
        path_result = ga_conn.fetch_one()
        if path_result:
            contrast_conn.execute(
                "INSERT INTO StimPath (stim_id, path) VALUES (%s, %s) ON DUPLICATE KEY UPDATE path = VALUES(path)",
                (parent_id, path_result)
            )

        # Copy parent's StimSpec
        ga_conn.execute("SELECT spec FROM StimSpec WHERE id = %s", (parent_id,))
        spec_result = ga_conn.fetch_one()
        if spec_result:
            contrast_conn.execute(
                "INSERT INTO StimSpec (id, spec) VALUES (%s, %s) ON DUPLICATE KEY UPDATE spec = VALUES(spec)",
                (parent_id, spec_result)
            )

        contrast_conn.mydb.commit()


def write_3d_instructions(contrast_conn, stimuli, contrasts):
    """Write instructions for 3D contrast variations."""
    for stim in stimuli:
        for contrast_value in contrasts:
            stim_id = time_util.now()
            sleep(.001)

            query = """
            INSERT INTO StimInstructions 
            (stim_id, parent_id, stim_type, texture_type, contrast)
            VALUES (%s, %s, %s, %s, %s)
            """

            params = (
                stim_id,
                stim.stim_id,
                'CONTRAST_3D_VARIATION',
                'SPECULAR',  # Using SPECULAR as default 3D type
                contrast_value
            )

            contrast_conn.execute(query, params)
            contrast_conn.mydb.commit()


def write_2d_match_instructions(contrast_conn, stimuli, contrasts):
    """Write instructions for 2D matches with corresponding contrasts."""
    for stim in stimuli:
        for contrast_value in contrasts:
            stim_id = time_util.now()
            sleep(.001)

            query = """
            INSERT INTO StimInstructions 
            (stim_id, parent_id, stim_type, texture_type, contrast)
            VALUES (%s, %s, %s, %s, %s)
            """

            params = (
                stim_id,
                stim.stim_id,
                '2D_MATCH',
                '2D',
                contrast_value
            )

            contrast_conn.execute(query, params)
            contrast_conn.mydb.commit()


def process_contrast_variations_through_alexnet(contrast_conn, unit_id):
    """Process all stimuli through AlexNet and save activations to contrast db."""
    parser = AlexNetIntanResponseParser(
        contrast_conn,
        "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/data/AlexNetONNX_with_conv3",
        unit_id
    )

    # Get all stim paths from StimInstructions
    query = """
    SELECT si.stim_id, sp.path 
    FROM StimInstructions si
    JOIN StimPath sp ON si.stim_id = sp.stim_id
    """
    contrast_conn.execute(query)
    stims = contrast_conn.fetch_all()

    for stim_id, path in stims:
        # Get activation using existing process_image method
        activation = parser.process_image(path)

        # Store in UnitActivations
        query = """
        INSERT INTO UnitActivations (stim_id, unit, activation) 
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE activation = %s
        """
        contrast_conn.execute(query, (
            stim_id,
            unit_id.to_string(),
            activation,
            activation
        ))
        contrast_conn.mydb.commit()


if __name__ == "__main__":
    main()