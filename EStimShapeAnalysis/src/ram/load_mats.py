from __future__ import annotations

import csv

import numpy as np
import scipy.io
import h5py


def top_stimulus(response_vector, stim_ids, mstick_specs, base_path, unit_id):
    max_indx = np.argsort(response_vector)[-1]
    top_mstick_spec = mstick_specs[max_indx]
    text_file = open("%s/%s/top_stimulus.txt" % (base_path, unit_id), "w")
    text_file.write(top_mstick_spec)
    text_file.close()



def main():
    base_path = "/home/r2_allen/Documents/Ram GA"
    num_generations = 6
    # unit = "170624_r-177"
    # unit = "170508_r-45"
    # unit = "170808_r-276"
    unit = "170807_r-274"

    stim_ids = []
    mstick_specs = []
    response_vector = []
    for gen_id in range(1, num_generations+1):
        (gen_stim_ids, gen_mstick_specs, gen_resp) = read_generation(base_path, unit, gen_id)
        stim_ids.extend(gen_stim_ids)
        mstick_specs.extend(gen_mstick_specs)
        response_vector.extend(gen_resp)

    top_stimulus(response_vector, stim_ids, mstick_specs, base_path, unit)

    with open(base_path + "/stimuli.csv", 'w', newline='') as myfile:
        wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        wr.writerow(mstick_specs)


def read_generation(base_path, unit_id, gen_id):
    # stim_ids
    stim_ids = scipy.io.loadmat("%s/%s/stim/%s_g-%s/stimIds.mat" % (base_path, unit_id, unit_id, gen_id))
    lineages = [lineage for lineage in stim_ids['currStimIds']]
    desc_ids = [stim_id[0] for lineage in lineages for stim_id in lineage]
    # stim_params
    stimParams = scipy.io.loadmat("%s/%s/stim/%s_g-%s/stimParams.mat" % (base_path, unit_id, unit_id, gen_id),
                                  simplify_cells=True)
    lineages = [lineage for lineage in stimParams['stimuli']]
    stimuli = [stimulus for lineage in lineages for stimulus in lineage]
    mstick_specs = [stimulus.shape.mstickspec for stimulus in stimuli]
    # resp
    resp = scipy.io.loadmat("%s/%s/resp/%s_g-%s/resp.mat" % (base_path, unit_id, unit_id, gen_id))
    response_vector = [np.average(response) for response in resp['resp']]

    return desc_ids, mstick_specs, response_vector


if __name__ == '__main__':
    main()