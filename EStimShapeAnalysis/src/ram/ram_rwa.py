from __future__ import annotations

import numpy as np
import scipy



def main():
    base_path = "/home/r2_allen/Documents/Ram GA"
    num_generations = 6
    # unit = "170624_r-177"
    # unit = "170508_r-45"
    # unit = "170808_r-276"
    unit = "170807_r-274"


    # RESPONSE VECTOR
    stim_ids, response_vector = read_all_stim_ids_and_responses_by_lineage(base_path, num_generations, unit)
    print(stim_ids)
    # STIM DATA


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
    for i in range(0, round(len(resp['resp'])/40)):
        response_vector.append([np.average(response) for response in resp['resp'][i*40:(i+1)*40]])

    return desc_ids, mstick_specs, response_vector

# stim_ids


if __name__ == '__main__':
    main()