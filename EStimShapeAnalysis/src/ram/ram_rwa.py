from __future__ import annotations

from math import pi

import jsonpickle
import numpy as np
import scipy
import xmltodict

from src.analysis.rwa import Binner, rwa, AutomaticBinner


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

    # RWA
    num_bins = 10
    binner_for_shaft_fields = {
        "theta": AutomaticBinner("theta", shaft_data, num_bins),
        "phi": AutomaticBinner("phi", shaft_data, num_bins),
        "radialPosition": AutomaticBinner("radialPosition", shaft_data, num_bins),
        "length": AutomaticBinner("length", shaft_data, num_bins),
        "curvature": AutomaticBinner("curvature", shaft_data, num_bins),
        "radius": AutomaticBinner("radius", shaft_data, num_bins),
    }

    # a percentage of the number of bins
    sigma_for_fields = {
        "theta": 1 / 8,
        "phi": 1 / 8,
        "radialPosition": 1 / 4,
        "length": 1 / 4,
        "curvature": 1 / 2,
        "radius": 1 / 4,
    }

    # CALCULATE RWA FOR EACH LINEAGE AND MULTIPLY
    response_weighted_average_shaft = rwa_from_lineages(shaft_data, response_vector, binner_for_shaft_fields,
                                                        sigma_for_fields)

    # SAVE
    filename = "%s/%s/rwa_shaft.json" % (base_path, unit)
    with open(filename, "w") as file:
        file.write(jsonpickle.encode(response_weighted_average_shaft))


def rwa_from_lineages(data, response_vector, binner_for_shaft_fields, sigma_for_fields):
    rwas = []
    for lineage_id, (lineage_stim_data, lineage_response_vector) in enumerate(zip(data, response_vector)):
        rwas.append(rwa(lineage_stim_data, lineage_response_vector, binner_for_shaft_fields, sigma_for_fields))
    rwas_labelled_matrices = [next(r) for r in rwas]
    rwa_prod = np.prod(np.array([rwa_labelled_matrix.matrix for rwa_labelled_matrix in rwas_labelled_matrices]), axis=0)
    response_weighted_average = rwas_labelled_matrices[0].copy_labels(rwa_prod)
    return response_weighted_average


def read_all_stim_ids_and_responses_by_lineage(base_path, num_generations, unit):
    stim_ids = []
    response_vector = []
    for gen_id in range(1, num_generations + 1):
        (gen_stim_ids, gen_mstick_specs, gen_resp) = read_generation_by_lineage(base_path, unit, gen_id)
        if (stim_ids == []):
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
