from __future__ import annotations

import numpy as np
import scipy
import xmltodict
from matplotlib import pyplot as plt

from src.analysis.ga.rwa import AutomaticBinner, rwa, raw_data, get_next, normalize_and_combine_rwas
from src.analysis.ga.oldmockga import hemisphericalize, condition_theta_and_phi
from clat.util import dictionary_util
from src.analysis.test_multidim_rwa import plot_data_and_rwa_variations


def load_data_by_lineage(data_path, stim_ids):
    shaft_datas = [[], []]
    junction_datas = [[], []]
    termination_datas = [[], []]
    for lineage_index, lineage in enumerate(stim_ids):
        for stim_id in lineage:
            file = open("%s/%s_spec.xml" % (data_path, stim_id), "r")
            spec = file.read()
            spec = xmltodict.parse(spec)
            shaft_datas[lineage_index].append(spec['AllenMStickData']['shaftData']['ShaftData'])
            junction_datas[lineage_index].append(spec['AllenMStickData']['junctionData']['JunctionData'])
            termination_datas[lineage_index].append(spec['AllenMStickData']['terminationData']['TerminationData'])
    return shaft_datas, junction_datas, termination_datas


def plot_top_n_responses(shaft_data, response_vector, n, binners_for_field):
    sorted_data = [(x, resp) for resp, x in
                   sorted(zip(response_vector, shaft_data), key=lambda pair: pair[0], reverse=True)]
    top_n = sorted_data[:n]

    fig = plt.figure(constrained_layout=True)
    axes = fig.subplots(1, 8)
    for stim, resp in top_n:
        values = []
        fields = []
        bin_middles = []
        for component in stim:
            value = []
            field = []
            dictionary_util.flatten_dictionary(component, value, field)
            values.append(value)
            if not fields:
                fields = field

        for value in values:
            bin_middle = []
            for field_index, field in enumerate(fields):
                bin_index, assigned_bin = binners_for_field[field].assign_bin(value[field_index])
                bin_middle.append(assigned_bin.middle)
            bin_middles.append(bin_middle)

        for index, (axis, field) in enumerate(zip(axes, fields)):
            x_points = [bin_middle[index] for bin_middle in bin_middles]
            y_points = [resp for _ in range(0, len(x_points))]
            axis.scatter(x_points, y_points)
            axis.set_title(field)

    plt.draw()


def main():
    base_path = "/home/r2_allen/Documents/Ram GA"
    num_generations = 6
    # unit = "170624_r-177"
    unit = "170508_r-45"
    # unit = "170808_r-276"
    # unit = "170807_r-274"

    # RESPONSE VECTOR
    stim_ids, response_vector = read_all_stim_ids_and_responses_by_lineage(base_path, num_generations, unit)

    # STIM DATA
    datas_path = "%s/%s/data" % (base_path, unit)
    shaft_data, junction_data, termination_data = load_data_by_lineage(datas_path, stim_ids)

    # CLEAN SHAFT DATA
    for lineage in shaft_data:
        for shaft in lineage:
            dictionary_util.apply_function_to_subdictionaries_values_with_keys(shaft, ["theta", "phi"],
                                                                               condition_theta_and_phi)
            dictionary_util.apply_function_to_subdictionaries_values_with_keys(shaft, ['orientation'],
                                                                               hemisphericalize)

    # RWA
    num_bins = 10
    binner_for_shaft_fields = {
        "theta": AutomaticBinner("theta", shaft_data, 9),
        "phi": AutomaticBinner("phi", shaft_data, 9),
        "radialPosition": AutomaticBinner("radialPosition", shaft_data, 10),
        "length": AutomaticBinner("length", shaft_data, 5),
        "curvature": AutomaticBinner("curvature", shaft_data, 5),
        "radius": AutomaticBinner("radius", shaft_data, 5),
    }

    # a percentage of the number of bins
    sigma_for_shaft_fields = {
        "theta": 0.2,
        "phi": 0.2,
        "radialPosition": 0.2,
        "length": 0.2,
        "curvature": 0.2,
        "radius": 0.2,
    }

    padding_for_shaft_fields = {
        "theta": "wrap",
        "phi": "wrap",
        "radialPosition": "nearest",
        "length": "nearest",
        "curvature": "nearest",
        "radius": "nearest",
    }
    summed_response_weighted_1, summed_unweighted_1 = get_next(
        raw_data(shaft_data[0], response_vector[0], binner_for_shaft_fields, sigma_for_shaft_fields,
                 padding_for_shaft_fields))
    summed_response_weighted_2, summed_unweighted_2 = get_next(
        raw_data(shaft_data[1], response_vector[1], binner_for_shaft_fields, sigma_for_shaft_fields,
                 padding_for_shaft_fields))
    response_weighted_average_1 = get_next(
        rwa(shaft_data[0], response_vector[0], binner_for_shaft_fields, sigma_for_shaft_fields,
            padding_for_shaft_fields))
    response_weighted_average_2 = get_next(
        rwa(shaft_data[1], response_vector[1], binner_for_shaft_fields, sigma_for_shaft_fields,
            padding_for_shaft_fields))

    plot_top_n_responses(shaft_data[0], response_vector[0], 100, binner_for_shaft_fields)
    plot_top_n_responses(shaft_data[1], response_vector[1], 100, binner_for_shaft_fields)
    response_weighted_averages = [response_weighted_average_1, response_weighted_average_2,
                                  normalize_and_combine_rwas([response_weighted_average_1, response_weighted_average_2])]
    summed_response_weighted = [summed_response_weighted_1,
                  summed_response_weighted_2]
    summed_unweighted = [summed_unweighted_1, summed_unweighted_2]
    plot_data_and_rwa_variations(response_weighted_averages, summed_response_weighted, summed_unweighted)

    # # CALCULATE RWA FOR EACH LINEAGE AND MULTIPLY
    # response_weighted_average_shaft = rwa_from_lineages(shaft_data, response_vector, binner_for_shaft_fields,
    #                                                     sigma_for_shaft_fields, padding_for_shaft_fields)
    #
    # # SAVE
    # filename = "%s/%s/rwa_shaft.json" % (base_path, unit)
    # with open(filename, "w") as file:
    #     file.write(jsonpickle.encode(response_weighted_average_shaft))
    #
    # plot_ram.main()


def rwa_from_lineages(data, response_vector, binner_for_shaft_fields, sigma_for_fields, padding_for_fields):
    rwas = []
    for lineage_id, (lineage_stim_data, lineage_response_vector) in enumerate(zip(data, response_vector)):
        rwas.append(rwa(lineage_stim_data, lineage_response_vector, binner_for_shaft_fields, sigma_for_fields,
                        padding_for_fields))

    rwa_prod = None
    for lineage_index, r in enumerate(rwas):
        lineage_rwa = get_next(r)
        if lineage_index == 0:
            template = lineage_rwa
            rwa_prod = np.ones_like(lineage_rwa.matrix)
        rwa_prod = np.multiply(rwa_prod, lineage_rwa.matrix)

    # rwas_labelled_matrices = [next(r) for r in rwas]
    # rwa_prod = np.prod(np.array([rwa_labelled_matrix.matrix for rwa_labelled_matrix in rwas_labelled_matrices]), axis=0)

    return template.copy_labels(rwa_prod)


def read_all_stim_ids_and_responses_by_lineage(base_path, num_generations, unit):
    stim_ids = []
    response_vector = []
    for gen_id in range(1, num_generations + 1):
        (gen_stim_ids, gen_mstick_specs, gen_resp) = read_generation_by_lineage(base_path, unit, gen_id)
        if stim_ids == []:
            stim_ids = gen_stim_ids
            response_vector = gen_resp
        else:
            for i in range(0, len(gen_stim_ids)):
                stim_ids[i].extend(gen_stim_ids[i])
                response_vector[i].extend(gen_resp[i])
    return stim_ids, response_vector


def read_generation_by_lineage(base_path, unit_id, gen_id):
    # stim_ids
    stim_ids = scipy.io.loadmat("%s/%s/stim/%s_g-%s/stimIds.mat" % (base_path, unit_id, unit_id, gen_id))
    lineages = [lineage for lineage in stim_ids['currStimIds']]
    desc_ids = []
    for lineage in lineages:
        desc_ids.append([stim_id[0] for stim_id in lineage])

    # stim_params
    stimParams = scipy.io.loadmat("%s/%s/stim/%s_g-%s/stimParams.mat" % (base_path, unit_id, unit_id, gen_id),
                                  simplify_cells=True)
    lineages = [lineage for lineage in stimParams['stimuli']]
    stimuli = []
    mstick_specs = []
    for lineage in lineages:
        stimuli.append([stimulus for stimulus in lineage])
        mstick_specs.append([stimulus.shape.mstickspec for stimulus in lineage])

    # resp
    resp = scipy.io.loadmat("%s/%s/resp/%s_g-%s/resp.mat" % (base_path, unit_id, unit_id, gen_id))
    response_vector = []
    for i in range(0, round(len(resp['resp']) / 40)):
        response_vector.append([np.average(response) for response in resp['resp'][i * 40:(i + 1) * 40]])

    return desc_ids, mstick_specs, response_vector


# stim_ids


if __name__ == '__main__':
    main()
