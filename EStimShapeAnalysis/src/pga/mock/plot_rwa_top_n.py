from __future__ import annotations

import xmltodict

from analysis.ga.rwa import RWAMatrix, get_point_coordinates
from clat.util.dictionary_util import apply_function_to_subdictionaries_values_with_keys
from pga.mock.mock_rwa_analysis import condition_theta_and_phi, hemisphericalize


def plot_top_n_stimuli_on_shaft(n, fig, rwa: RWAMatrix, conn):
    top_n_response, top_n_stim_xml = _fetch_top_n_stim_response_and_xml(conn, n)
    top_n_shaft_data = _process_shaft_xml(top_n_stim_xml)
    top_n_shaft_points = _convert_data_to_coordinates(rwa, top_n_shaft_data)
    _plot_shaft_points(fig, top_n_response, top_n_shaft_points)


def plot_top_n_stimuli_on_termination(n, fig, rwa: RWAMatrix, conn):
    top_n_response, top_n_stim_xml = _fetch_top_n_stim_response_and_xml(conn, n)
    top_n_termination_data = _process_termination_xml(top_n_stim_xml)
    top_n_termination_points = _convert_data_to_coordinates(rwa, top_n_termination_data)
    print(top_n_termination_points)
    _plot_termination_points(fig, top_n_response, top_n_termination_points)


def plot_top_n_junctions_on_fig(n, fig, junction_rwa, conn):
    top_n_response, top_n_junction_xml = _fetch_top_n_stim_response_and_xml(conn, n)
    top_n_junction_data = _process_junction_xml(top_n_junction_xml)
    top_n_junction_points = _convert_data_to_coordinates(junction_rwa, top_n_junction_data)
    print(top_n_junction_points)
    _plot_junction_points(fig, top_n_response, top_n_junction_points)


def _process_junction_xml(top_n_junction_xml):
    top_n_junction_data = []
    for junc_xml in top_n_junction_xml:
        junc_data = xmltodict.parse(junc_xml)
        junc_data = junc_data["AllenMStickData"]["junctionData"]["JunctionData"]
        apply_function_to_subdictionaries_values_with_keys(junc_data, ["theta", "phi"],
                                                           condition_theta_and_phi)
        top_n_junction_data.append(junc_data)
    return top_n_junction_data


def _plot_junction_points(fig, top_n_response, top_n_junction_points):
    axes = fig.axes
    color_cycle = ['black', 'red', 'green', 'blue']  # Cycle of colors for different stimuli

    # Dimensions to plot
    dimensions = ['Angular Position Theta', 'Angular Position Phi', 'Radial Position',
                  'Angle Bisector Direction Theta', 'Angle Bisector Direction Phi', 'Radius',
                  'Angular Subtense', 'Planar Rotation']

    for stim_index, junction_points in enumerate(top_n_junction_points):
        response = top_n_response[stim_index]
        y_values = [response for _ in junction_points]

        for dim_index, dimension in enumerate(dimensions):
            # Extract the dimension values for all points
            dim_values = [point[dim_index] for point in junction_points]
            color = color_cycle[stim_index % len(color_cycle)]  # Cycle through colors

            # Plot each point for the current dimension
            for point_index, point in enumerate(dim_values):
                axes[dim_index].scatter(point, y_values[point_index], color=color)

            # Optional: Set title or labels for each axis here if needed
            axes[dim_index].set_title(dimension)


def _plot_termination_points(fig, top_n_response, top_n_termination_points):
    colors = ['black', 'red', 'green', 'blue']  # Example colors for different termination points

    # Assuming each subplot in fig corresponds to a dimension plotted in plot_termination_rwa_1d
    # The order and number of axes should match the dimensions you wish to plot
    axes = fig.axes

    for stim_index, termination_points in enumerate(top_n_termination_points):
        response = top_n_response[stim_index]
        y_values = [response for _ in termination_points]

        # Extract dimensions from termination_points as per your data structure.
        # Here, we use placeholders assuming each termination point is a tuple/list with these dimensions
        # Adjust according to your actual data structure
        angular_position_theta = [point[0] for point in termination_points]
        angular_position_phi = [point[1] for point in termination_points]
        radial_position = [point[2] for point in termination_points]
        direction_theta = [point[3] for point in termination_points]
        direction_phi = [point[4] for point in termination_points]
        radius = [point[5] for point in termination_points]

        # Plot each dimension on its corresponding subplot
        for i, dimension in enumerate([angular_position_theta, angular_position_phi, radial_position,
                                       direction_theta, direction_phi, radius]):
            for point_index, point in enumerate(dimension):
                axes[i].scatter(point, y_values[point_index], color=colors[stim_index % len(colors)])

    # Set titles or labels for each axis as necessary, matching the plot_termination_rwa_1d function
    axes[0].set_title("Angular Position Theta")
    axes[1].set_title("Angular Position Phi")
    axes[2].set_title("Radial Position")
    axes[3].set_title("Direction Theta")
    axes[4].set_title("Direction Phi")
    axes[5].set_title("Radius")


def _process_termination_xml(top_n_stim_xml):
    top_n_termination_data = []
    for stim_xml in top_n_stim_xml:
        termination_data = xmltodict.parse(stim_xml)["AllenMStickData"]["terminationData"]["TerminationData"]
        apply_function_to_subdictionaries_values_with_keys(termination_data, ["theta", "phi"],
                                                           condition_theta_and_phi)
        top_n_termination_data.append(termination_data)
    return top_n_termination_data


def _plot_shaft_points(fig, top_n_response, top_n_shaft_points):
    # Assuming the axes are ordered correctly for the dimensions you're plotting
    axes = fig.axes
    color_cycle = ['black', 'red', 'green', 'blue']  # Cycle of colors for different stimuli

    # Dimensions to plot. Adjust the indices as per the data structure of your shaft points
    dimensions = ['Angular Position Theta', 'Angular Position Phi', 'Radial Position',
                  'Orientation Theta', 'Orientation Phi', 'Radius', 'Length', 'Curvature']

    for stim_index, shaft_points in enumerate(top_n_shaft_points):
        response = top_n_response[stim_index]
        y_values = [response for _ in shaft_points]

        for dim_index, dimension in enumerate(dimensions):
            # Extract the dimension values for all points
            dim_values = [point[dim_index] for point in shaft_points]
            color = color_cycle[stim_index % len(color_cycle)]  # Cycle through colors

            # Plot each point for the current dimension
            for point_index, point in enumerate(dim_values):
                axes[dim_index].scatter(point, y_values[point_index], color=color)

            # Optional: Set title or labels for each axis here if needed
            axes[dim_index].set_title(dimension)


def _convert_data_to_coordinates(rwa, top_n_data) -> list[list[list[float]]]:
    # Get point matrix for each shaft
    top_n_points = []
    for data in top_n_data:
        point_coordinates = get_point_coordinates(rwa, data)
        top_n_points.append(point_coordinates)
    return top_n_points


def _process_shaft_xml(top_n_stim_data) -> list[dict]:
    # Parse XML
    top_n_shaft_data = []
    for stim_data in top_n_stim_data:
        stim_data = xmltodict.parse(stim_data)
        shaft_data = stim_data["AllenMStickData"]["shaftData"]["ShaftData"]
        apply_function_to_subdictionaries_values_with_keys(shaft_data, ["theta", "phi"],
                                                           condition_theta_and_phi)
        apply_function_to_subdictionaries_values_with_keys(shaft_data, ['orientation'],
                                                           hemisphericalize)
        top_n_shaft_data.append(shaft_data)
    return top_n_shaft_data


def _fetch_top_n_stim_response_and_xml(conn, n):
    conn.execute("SELECT stim_id, response FROM StimGaInfo ORDER BY response DESC LIMIT %s", params=(n,))
    top_n_stim_id_and_response = conn.fetch_all()
    top_n_stim_ids = [stim[0] for stim in top_n_stim_id_and_response]
    top_n_response = [float(stim[1]) for stim in top_n_stim_id_and_response]
    print(top_n_response)
    # top_n_stim_ids = conn.fetch_all()
    # top_n_stim_ids = [stim_id[0] for stim_id in top_n_stim_ids]
    # Get Data from StimSpec for each top_n_stim_ids
    top_n_stim_data = []
    for stim_id in top_n_stim_ids:
        conn.execute("SELECT data FROM StimSpec WHERE id = %s", params=(stim_id,))
        top_n_stim_data.append(conn.fetch_one())
    return top_n_response, top_n_stim_data
