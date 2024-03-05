from __future__ import annotations

import numpy as np
import xmltodict
from matplotlib import pyplot as plt

from analysis.ga.rwa import RWAMatrix, get_point_coordinates, get_point_indices, Binner
from clat.util.connection import Connection
from clat.util.dictionary_util import apply_function_to_subdictionaries_values_with_keys
from pga.mock.mock_rwa_analysis import condition_theta_and_phi, hemisphericalize


def find_distances_to_peak(rwa: RWAMatrix, n: int, conn: Connection, type: str):
    matrix = rwa.matrix

    # get peak into the form of a list of bin - indices
    peak_temp_form = np.unravel_index(np.argsort(matrix, axis=None)[-1:], matrix.shape)
    peak_index_list = []
    for dimension in peak_temp_form:
        peak_index_list.append(dimension[0])

    top_n_response, top_n_stim_xml = _fetch_top_n_stim_response_and_xml(conn, n)
    if type == 'shaft':
        top_n_data = _process_shaft_xml(top_n_stim_xml)
    elif type == 'termination':
        top_n_data = _process_termination_xml(top_n_stim_xml)
    elif type == 'junction':
        top_n_data = _process_junction_xml(top_n_stim_xml)
    else:
        raise ValueError("Invalid type")
    top_n_stimuli = _convert_data_to_bin_indices(rwa, top_n_data)

    # get the closest points to the peak
    distances_to_peak_per_component_per_stim = []
    binners_for_axes = list(rwa.binners_for_axes.values())
    limits_for_axes = [(0, binner.num_bins - 1) for binner in binners_for_axes]
    for stimulus_points in top_n_stimuli:
        distances_to_peak_per_stim = []
        for component in stimulus_points:
            d = distance(peak_index_list, component, rwa.padding_for_axes, limits_for_axes)
            distances_to_peak_per_stim.append(d)
        distances_to_peak_per_component_per_stim.append(distances_to_peak_per_stim)

    return distances_to_peak_per_component_per_stim


def distance(peak, component, padding_for_axes, limits_for_axes):
    distance_for_dimension = []
    for i in range(len(component)):
        limit = limits_for_axes[i]
        if padding_for_axes[str(i)] == 'wrap':
            # Calculate the circular distance considering wrap around
            total_length = limit[1] - limit[0]
            distance_1 = abs(peak[i] - component[i])
            distance_2 = total_length - distance_1
            distance_for_dimension.append(min(distance_1, distance_2))
        else:
            # Standard Euclidean distance for non-wrap dimensions
            distance_for_dimension.append(abs(peak[i] - component[i]))

    # Calculate the Euclidean distance from the dimension-wise distances
    # euclidean_distance = sum(d ** 2 for d in distance_for_dimension) ** 0.5
    manhattan_distance = sum(distance_for_dimension)
    return manhattan_distance


def plot_top_n_stimuli_on_shaft(n, fig, rwa: RWAMatrix, conn):
    top_n_response, top_n_stim_xml = _fetch_top_n_stim_response_and_xml(conn, n)
    top_n_shaft_data = _process_shaft_xml(top_n_stim_xml)
    top_n_shaft_points = _convert_data_to_bin_indices(rwa, top_n_shaft_data)
    _plot_shaft_points(fig, top_n_response, top_n_shaft_points, rwa.binners_for_axes)


def plot_top_n_stimuli_on_termination(n, fig, rwa: RWAMatrix, conn) -> list[list[list[float]]]:
    top_n_response, top_n_stim_xml = _fetch_top_n_stim_response_and_xml(conn, n)
    top_n_termination_data = _process_termination_xml(top_n_stim_xml)
    top_n_termination_points = _convert_data_to_bin_indices(rwa, top_n_termination_data)
    _plot_termination_points(fig, top_n_response, top_n_termination_points, rwa.binners_for_axes)
    return top_n_termination_points


def plot_top_n_junctions_on_fig(n, fig, junction_rwa, conn) -> list[list[list[float]]]:
    top_n_response, top_n_junction_xml = _fetch_top_n_stim_response_and_xml(conn, n)
    top_n_junction_data = _process_junction_xml(top_n_junction_xml)
    top_n_junction_points = _convert_data_to_bin_indices(junction_rwa, top_n_junction_data)
    _plot_junction_points(fig, top_n_response, top_n_junction_points, junction_rwa.binners_for_axes)
    return top_n_junction_points


def _process_junction_xml(top_n_junction_xml):
    top_n_junction_data = []
    for junc_xml in top_n_junction_xml:
        junc_data = xmltodict.parse(junc_xml)
        junc_data = junc_data["AllenMStickData"]["junctionData"]["JunctionData"]
        apply_function_to_subdictionaries_values_with_keys(junc_data, ["theta", "phi"],
                                                           condition_theta_and_phi)
        top_n_junction_data.append(junc_data)
    return top_n_junction_data


def _plot_shaft_points(fig, top_n_response, top_n_shaft_points, binners_for_axes: dict[int, Binner]):
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
            dim_values = [binners_for_axes[str(dim_index)].bins[point[dim_index]].middle for point in shaft_points]

            # Plot each point for the current dimension
            for point_index, point in enumerate(dim_values):
                color = color_cycle[point_index % len(color_cycle)]  # Cycle through colors
                axes[dim_index].scatter(point, y_values[point_index], color=color)


def _plot_termination_points(fig, top_n_response, top_n_termination_points, binners_for_axes: dict[int, Binner]):
    colors = ['black', 'red', 'green', 'blue']  # Example colors for different termination points

    # Assuming each subplot in fig corresponds to a dimension plotted in plot_termination_rwa_1d
    # The order and number of axes should match the dimensions you wish to plot
    axes = fig.axes

    for stim_index, stimuli_points in enumerate(top_n_termination_points):
        response = top_n_response[stim_index]
        y_values = [response for _ in stimuli_points]

        # Extract dimensions from termination_points as per your data structure.
        # Here, we use placeholders assuming each termination point is a tuple/list with these dimensions
        # Adjust according to your actual data structure
        angular_position_theta = [point[0] for point in stimuli_points]
        angular_position_phi = [point[1] for point in stimuli_points]
        radial_position = [point[2] for point in stimuli_points]
        direction_theta = [point[3] for point in stimuli_points]
        direction_phi = [point[4] for point in stimuli_points]
        radius = [point[5] for point in stimuli_points]

        # Plot each dimension on its corresponding subplot
        for dim_index, dimension in enumerate([angular_position_theta, angular_position_phi, radial_position,
                                               direction_theta, direction_phi, radius]):
            for component_index, component_bin_index in enumerate(dimension):
                x_value = binners_for_axes[str(dim_index)].bins[component_bin_index].middle
                y_value = y_values[component_index]
                axes[dim_index].scatter(x_value, y_value, color=colors[component_index % len(colors)])

            # Automatically adjust the y-axis to fit all points after plotting
            axes[dim_index].autoscale(enable=True, axis='y', tight=None)


    # Set titles or labels for each axis as necessary, matching the plot_termination_rwa_1d function
    axes[0].set_title("Angular Position Theta")
    axes[1].set_title("Angular Position Phi")
    axes[2].set_title("Radial Position")
    axes[3].set_title("Direction Theta")
    axes[4].set_title("Direction Phi")
    axes[5].set_title("Radius")




def _plot_junction_points(fig, top_n_response, top_n_junction_points, binners_for_axes: dict[int, Binner]):
    axes = fig.axes
    color_cycle = ['black', 'red', 'green', 'blue', 'yellow', 'cyan', 'purple']  # Cycle of colors for different stimuli

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

            # Plot each point for the current dimension
            for component_index, component_bin_index in enumerate(dim_values):
                color = color_cycle[component_index % len(color_cycle)]  # Cycle through colors
                x_value = binners_for_axes[str(dim_index)].bins[component_bin_index].middle
                y_value = y_values[component_index]
                axes[dim_index].scatter(x_value, y_value, color=color)

            # Optional: Set title or labels for each axis here if needed
            axes[dim_index].set_title(dimension)
            # Automatically adjust the y-axis to fit all points after plotting
            axes[dim_index].autoscale(enable=True, axis='y', tight=None)



def _process_termination_xml(top_n_stim_xml):
    top_n_termination_data = []
    for stim_xml in top_n_stim_xml:
        termination_data = xmltodict.parse(stim_xml)["AllenMStickData"]["terminationData"]["TerminationData"]
        apply_function_to_subdictionaries_values_with_keys(termination_data, ["theta", "phi"],
                                                           condition_theta_and_phi)
        top_n_termination_data.append(termination_data)
    return top_n_termination_data


def _convert_data_to_coordinates(rwa, top_n_data) -> list[list[list[float]]]:
    # Get point matrix for each shaft
    top_n_points = []
    for data in top_n_data:
        point_coordinates = get_point_coordinates(rwa, data)
        top_n_points.append(point_coordinates)
    return top_n_points


def _convert_data_to_bin_indices(rwa, top_n_data) -> list[list[list[int]]]:
    # Get point matrix for each shaft
    top_n_points = []
    for data in top_n_data:
        point_bin_indices = get_point_indices(rwa, data)
        top_n_points.append(point_bin_indices)
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

    top_n_stim_data = []
    for stim_id in top_n_stim_ids:
        conn.execute("SELECT data FROM StimSpec WHERE id = %s", params=(stim_id,))
        top_n_stim_data.append(conn.fetch_one())
    return top_n_response, top_n_stim_data

def fetch_top_n_stim_ids(conn, n):
    conn.execute("SELECT stim_id FROM StimGaInfo ORDER BY response DESC LIMIT %s", params=(n,))
    top_n_stim_id = conn.fetch_all()
    return [stim[0] for stim in top_n_stim_id]
