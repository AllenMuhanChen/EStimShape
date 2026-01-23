from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
from clat.util import time_util
from src.analysis.nafc.nafc_database_fields import IsCorrectField, IsHypothesizedField, NoiseChanceField, \
    NumRandDistractorsField, StimTypeField, ChoiceField, GenIdField, EStimEnabledField, BaseMStickIdField, IsDeltaField, \
    EStimPolarityField, EStimSpecIdField, StimSpecIdField, IsHypothesizedFieldLegacy, EStimEnabledFieldLegacy
from src.analysis.nafc.psychometric_curves import collect_choice_trials



def compile_251226_0(exp_conn):
    # Time range
    start_gen_id = 8
    max_gen_id = 19
    start_gen_id_estim_on = 0
    max_gen_id_estim_on = float('inf')
    since_date = time_util.from_date_to_now(2024, 7, 10)
    trial_tstamps = collect_choice_trials(exp_conn, since_date)
    fields = CachedFieldList()
    fields.append(StimSpecIdField(exp_conn))
    fields.append(IsCorrectField(exp_conn))
    # fields.append(IsHypothesizedFieldLegacy(exp_conn))
    fields.append(NoiseChanceField(exp_conn))
    fields.append(NumRandDistractorsField(exp_conn))
    # fields.append(EStimSpecIdField(exp_conn))
    fields.append(StimTypeField(exp_conn))
    fields.append(ChoiceField(exp_conn))
    fields.append(GenIdField(exp_conn))
    fields.append(EStimEnabledFieldLegacy(exp_conn))
    fields.append(BaseMStickIdField(exp_conn))
    # fields.append(IsDeltaField(exp_conn))
    # fields.append(EStimPolarityField(exp_conn))
    data = fields.to_data(trial_tstamps)
    # Filter data by GenId
    data = data[(data['GenId'] >= start_gen_id) & (data['GenId'] <= max_gen_id)]
    # Filter for experimental trials only
    data_exp = data[data['StimType'] == 'EStimShapeVariantsNAFCStim']

    if 'TrialStartStop' in data_exp.columns:
        data_exp['trial_start'] = data_exp['TrialStartStop'].apply(lambda x: x.start if x is not None else None)
        data_exp['trial_end'] = data_exp['TrialStartStop'].apply(lambda x: x.stop if x is not None else None)
        data_exp = data_exp.drop(columns=['TrialStartStop'])

    # data_exp['is_hypothesized_choice'] = data_exp['IsCorrect']
    data_exp['estim_spec_id'] = data_exp['EStimEnabled'].apply(lambda x: 1 if x else 0)
    data_exp['is_hypothesized_choice'] = data_exp['IsCorrect']
    data_exp = data_exp.rename(columns={
        'StimSpecId': 'task_id',
        'EStimEnabled': 'is_estim_on',
        'IsCorrect': 'is_correct_choice',
        'NoiseChance': 'noise_chance',
        'BaseMStickId': 'base_mstick_id',
        'GenId': 'gen_id',
    })

    return data_exp

def compile_251231_0(exp_conn):
    # Time range
    start_gen_id = 4
    max_gen_id = 6
    start_gen_id_estim_on = 0
    max_gen_id_estim_on = float('inf')
    since_date = time_util.from_date_to_now(2024, 7, 10)
    trial_tstamps = collect_choice_trials(exp_conn, since_date)
    fields = CachedFieldList()
    fields.append(StimSpecIdField(exp_conn))
    fields.append(IsCorrectField(exp_conn))
    # fields.append(IsHypothesizedFieldLegacy(exp_conn))
    fields.append(NoiseChanceField(exp_conn))
    fields.append(NumRandDistractorsField(exp_conn))
    # fields.append(EStimSpecIdField(exp_conn))
    fields.append(StimTypeField(exp_conn))
    fields.append(ChoiceField(exp_conn))
    fields.append(GenIdField(exp_conn))
    fields.append(EStimEnabledFieldLegacy(exp_conn))
    fields.append(BaseMStickIdField(exp_conn))
    # fields.append(IsDeltaField(exp_conn))
    # fields.append(EStimPolarityField(exp_conn))
    data = fields.to_data(trial_tstamps)
    # Filter data by GenId
    data = data[(data['GenId'] >= start_gen_id) & (data['GenId'] <= max_gen_id)]
    # Filter for experimental trials only
    data_exp = data[data['StimType'] == 'EStimShapeVariantsNAFCStim']

    if 'TrialStartStop' in data_exp.columns:
        data_exp['trial_start'] = data_exp['TrialStartStop'].apply(lambda x: x.start if x is not None else None)
        data_exp['trial_end'] = data_exp['TrialStartStop'].apply(lambda x: x.stop if x is not None else None)
        data_exp = data_exp.drop(columns=['TrialStartStop'])

    # data_exp['is_hypothesized_choice'] = data_exp['IsCorrect']
    data_exp['estim_spec_id'] = data_exp['EStimEnabled'].apply(lambda x: 1 if x else 0)
    data_exp['is_hypothesized_choice'] = data_exp['IsCorrect']
    data_exp = data_exp.rename(columns={
        'StimSpecId': 'task_id',
        'EStimEnabled': 'is_estim_on',
        'IsCorrect': 'is_correct_choice',
        'NoiseChance': 'noise_chance',
        'BaseMStickId': 'base_mstick_id',
        'GenId': 'gen_id',
    })

    return data_exp

def compile_260107_0(exp_conn):
    # Time range
    start_gen_id = 8
    max_gen_id = 14
    start_gen_id_estim_on = 0
    max_gen_id_estim_on = float('inf')
    since_date = time_util.from_date_to_now(2024, 7, 10)
    trial_tstamps = collect_choice_trials(exp_conn, since_date)
    fields = CachedFieldList()
    fields.append(StimSpecIdField(exp_conn))
    fields.append(IsCorrectField(exp_conn))
    fields.append(IsHypothesizedFieldLegacy(exp_conn))
    fields.append(NoiseChanceField(exp_conn))
    fields.append(NumRandDistractorsField(exp_conn))
    # fields.append(EStimSpecIdField(exp_conn))
    fields.append(StimTypeField(exp_conn))
    fields.append(ChoiceField(exp_conn))
    fields.append(GenIdField(exp_conn))
    fields.append(EStimEnabledFieldLegacy(exp_conn))
    fields.append(BaseMStickIdField(exp_conn))
    fields.append(IsDeltaField(exp_conn))
    # fields.append(EStimPolarityField(exp_conn))
    data = fields.to_data(trial_tstamps)
    # Filter data by GenId
    data = data[(data['GenId'] >= start_gen_id) & (data['GenId'] <= max_gen_id)]
    # Filter for experimental trials only
    data_exp = data[data['StimType'] == 'EStimShapeVariantsDeltaNAFCStim']

    if 'TrialStartStop' in data_exp.columns:
        data_exp['trial_start'] = data_exp['TrialStartStop'].apply(lambda x: x.start if x is not None else None)
        data_exp['trial_end'] = data_exp['TrialStartStop'].apply(lambda x: x.stop if x is not None else None)
        data_exp = data_exp.drop(columns=['TrialStartStop'])

    # data_exp['is_hypothesized_choice'] = data_exp['IsCorrect']
    data_exp['estim_spec_id'] = data_exp['EStimEnabled'].apply(lambda x: 1 if x else 0)
    if 'IsDelta' in data_exp.columns:
        data_exp['trial_type'] = data_exp['IsDelta'].apply(lambda x: "Hypothesized Shape" if not x else "Delta Shape")
    data_exp = data_exp.rename(columns={
        'StimSpecId': 'task_id',
        'IsHypothesized': 'is_hypothesized_choice',
        'EStimEnabled': 'is_estim_on',
        'IsCorrect': 'is_correct_choice',
        'NoiseChance': 'noise_chance',
        'BaseMStickId': 'base_mstick_id',
        'GenId': 'gen_id',
    })

    return data_exp


def compile_260108_0(exp_conn):
    # Time range
    start_gen_id = 9 #start switch to anodic
    max_gen_id = 16 #17 we change to 3.5 uA
    start_gen_id_estim_on = 0
    max_gen_id_estim_on = float('inf')
    since_date = time_util.from_date_to_now(2024, 7, 10)
    trial_tstamps = collect_choice_trials(exp_conn, since_date)
    fields = CachedFieldList()
    fields.append(StimSpecIdField(exp_conn))
    fields.append(IsCorrectField(exp_conn))
    # fields.append(IsHypothesizedFieldLegacy(exp_conn))
    fields.append(NoiseChanceField(exp_conn))
    fields.append(NumRandDistractorsField(exp_conn))
    # fields.append(EStimSpecIdField(exp_conn))
    fields.append(StimTypeField(exp_conn))
    fields.append(ChoiceField(exp_conn))
    fields.append(GenIdField(exp_conn))
    fields.append(EStimEnabledFieldLegacy(exp_conn))
    fields.append(BaseMStickIdField(exp_conn))
    # fields.append(IsDeltaField(exp_conn))
    # fields.append(EStimPolarityField(exp_conn))
    data = fields.to_data(trial_tstamps)
    # Filter data by GenId
    data = data[(data['GenId'] >= start_gen_id) & (data['GenId'] <= max_gen_id)]
    # Filter for experimental trials only
    data_exp = data[data['StimType'] == 'EStimShapeVariantsNAFCStim']

    if 'TrialStartStop' in data_exp.columns:
        data_exp['trial_start'] = data_exp['TrialStartStop'].apply(lambda x: x.start if x is not None else None)
        data_exp['trial_end'] = data_exp['TrialStartStop'].apply(lambda x: x.stop if x is not None else None)
        data_exp = data_exp.drop(columns=['TrialStartStop'])

    # data_exp['is_hypothesized_choice'] = data_exp['IsCorrect']
    data_exp['estim_spec_id'] = data_exp['EStimEnabled'].apply(lambda x: 1 if x else 0)
    data_exp['is_hypothesized_choice'] = data_exp['IsCorrect']
    data_exp = data_exp.rename(columns={
        'StimSpecId': 'task_id',
        # 'IsHypothesized': 'is_hypothesized_choice',
        'EStimEnabled': 'is_estim_on',
        'IsCorrect': 'is_correct_choice',
        'NoiseChance': 'noise_chance',
        'BaseMStickId': 'base_mstick_id',
        'GenId': 'gen_id',
    })

    return data_exp

def compile_260113_0(exp_conn):
    # Time range
    start_gen_id = 3
    max_gen_id = 7
    start_gen_id_estim_on = 0
    max_gen_id_estim_on = float('inf')
    since_date = time_util.from_date_to_now(2024, 7, 10)
    trial_tstamps = collect_choice_trials(exp_conn, since_date)
    fields = CachedFieldList()
    fields.append(StimSpecIdField(exp_conn))
    fields.append(IsCorrectField(exp_conn))
    fields.append(IsHypothesizedFieldLegacy(exp_conn))
    fields.append(NoiseChanceField(exp_conn))
    fields.append(NumRandDistractorsField(exp_conn))
    fields.append(EStimSpecIdField(exp_conn))
    fields.append(StimTypeField(exp_conn))
    fields.append(ChoiceField(exp_conn))
    fields.append(GenIdField(exp_conn))
    fields.append(EStimEnabledField(exp_conn))
    fields.append(BaseMStickIdField(exp_conn))
    fields.append(IsDeltaField(exp_conn))
    fields.append(EStimPolarityField(exp_conn))
    data = fields.to_data(trial_tstamps)
    # Filter data by GenId
    data = data[(data['GenId'] >= start_gen_id) & (data['GenId'] <= max_gen_id)]
    # Filter for experimental trials only
    data_exp = data[data['StimType'] == 'EStimShapeVariantsDeltaNAFCStim']

    if 'TrialStartStop' in data_exp.columns:
        data_exp['trial_start'] = data_exp['TrialStartStop'].apply(lambda x: x.start if x is not None else None)
        data_exp['trial_end'] = data_exp['TrialStartStop'].apply(lambda x: x.stop if x is not None else None)
        data_exp = data_exp.drop(columns=['TrialStartStop'])

    if 'IsDelta' in data_exp.columns:
        data_exp['trial_type'] = data_exp['IsDelta'].apply(lambda x: "Hypothesized Shape" if not x else "Delta Shape")
    data_exp = data_exp.rename(columns={
        'StimSpecId': 'task_id',
        'EStimEnabled': 'is_estim_on',
        'IsCorrect': 'is_correct_choice',
        'IsHypothesized': 'is_hypothesized_choice',
        'EStimSpecId': 'estim_spec_id',
        'NoiseChance': 'noise_chance',
        'BaseMStickId': 'base_mstick_id',
        'GenId': 'gen_id',
    })

    return data_exp
def compile_260115_0(exp_conn):
    # Time range
    start_gen_id = 3
    max_gen_id = float('inf')
    start_gen_id_estim_on = 0
    max_gen_id_estim_on = float('inf')
    since_date = time_util.from_date_to_now(2024, 7, 10)
    trial_tstamps = collect_choice_trials(exp_conn, since_date)
    fields = CachedFieldList()
    fields.append(StimSpecIdField(exp_conn))
    fields.append(IsCorrectField(exp_conn))
    fields.append(IsHypothesizedField(exp_conn))
    fields.append(NoiseChanceField(exp_conn))
    fields.append(NumRandDistractorsField(exp_conn))
    fields.append(EStimSpecIdField(exp_conn))
    fields.append(StimTypeField(exp_conn))
    fields.append(ChoiceField(exp_conn))
    fields.append(GenIdField(exp_conn))
    fields.append(EStimEnabledField(exp_conn))
    fields.append(BaseMStickIdField(exp_conn))
    fields.append(IsDeltaField(exp_conn))
    fields.append(EStimPolarityField(exp_conn))
    data = fields.to_data(trial_tstamps)
    # Filter data by GenId
    data = data[(data['GenId'] >= start_gen_id) & (data['GenId'] <= max_gen_id)]
    # Filter for experimental trials only
    data_exp = data[data['StimType'] == 'EStimShapeVariantsDeltaNAFCStim']

    if 'TrialStartStop' in data_exp.columns:
        data_exp['trial_start'] = data_exp['TrialStartStop'].apply(lambda x: x.start if x is not None else None)
        data_exp['trial_end'] = data_exp['TrialStartStop'].apply(lambda x: x.stop if x is not None else None)
        data_exp = data_exp.drop(columns=['TrialStartStop'])

    if 'IsDelta' in data_exp.columns:
        data_exp['trial_type'] = data_exp['IsDelta'].apply(lambda x: "Hypothesized Shape" if not x else "Delta Shape")
    data_exp = data_exp.rename(columns={
        'StimSpecId': 'task_id',
        'EStimEnabled': 'is_estim_on',
        'IsCorrect': 'is_correct_choice',
        'IsHypothesized': 'is_hypothesized_choice',
        'EStimSpecId': 'estim_spec_id',
        'NoiseChance': 'noise_chance',
        'BaseMStickId': 'base_mstick_id',
        'GenId': 'gen_id',
    })

    return data_exp
def compile_260120_0(exp_conn):
    # Time range
    start_gen_id = 3
    max_gen_id = 8
    start_gen_id_estim_on = 0
    max_gen_id_estim_on = float('inf')
    since_date = time_util.from_date_to_now(2024, 7, 10)
    trial_tstamps = collect_choice_trials(exp_conn, since_date)
    fields = CachedFieldList()
    fields.append(StimSpecIdField(exp_conn))
    fields.append(IsCorrectField(exp_conn))
    fields.append(IsHypothesizedField(exp_conn))
    fields.append(NoiseChanceField(exp_conn))
    fields.append(NumRandDistractorsField(exp_conn))
    fields.append(EStimSpecIdField(exp_conn))
    fields.append(StimTypeField(exp_conn))
    fields.append(ChoiceField(exp_conn))
    fields.append(GenIdField(exp_conn))
    fields.append(EStimEnabledField(exp_conn))
    fields.append(BaseMStickIdField(exp_conn))
    fields.append(IsDeltaField(exp_conn))
    fields.append(EStimPolarityField(exp_conn))
    data = fields.to_data(trial_tstamps)
    # Filter data by GenId
    data = data[(data['GenId'] >= start_gen_id) & (data['GenId'] <= max_gen_id)]
    # Filter for experimental trials only
    data_exp = data[data['StimType'] == 'EStimShapeVariantsDeltaNAFCStim']

    if 'TrialStartStop' in data_exp.columns:
        data_exp['trial_start'] = data_exp['TrialStartStop'].apply(lambda x: x.start if x is not None else None)
        data_exp['trial_end'] = data_exp['TrialStartStop'].apply(lambda x: x.stop if x is not None else None)
        data_exp = data_exp.drop(columns=['TrialStartStop'])

    if 'IsDelta' in data_exp.columns:
        data_exp['trial_type'] = data_exp['IsDelta'].apply(lambda x: "Hypothesized Shape" if not x else "Delta Shape")
    data_exp = data_exp.rename(columns={
        'StimSpecId' : 'task_id',
        'EStimEnabled': 'is_estim_on',
        'IsCorrect': 'is_correct_choice',
        'IsHypothesized': 'is_hypothesized_choice',
        'EStimSpecId': 'estim_spec_id',
        'NoiseChance': 'noise_chance',
        'BaseMStickId': 'base_mstick_id',
        'GenId': 'gen_id',
    })

    return data_exp
