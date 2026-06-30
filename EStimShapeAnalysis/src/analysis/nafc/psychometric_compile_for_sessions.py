from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
from clat.util import time_util
from src.analysis.nafc.nafc_database_fields import IsCorrectField, IsHypothesizedField, NoiseChanceField, \
    NumRandDistractorsField, NumChoicesField, NumProceduralDistractorsField, StimTypeField, ChoiceField, GenIdField, \
    EStimEnabledField, BaseMStickIdField, PickedBaseMStickIdField, IsDeltaField, \
    EStimPolarityField, EStimSpecIdField, StimSpecIdField, IsHypothesizedFieldLegacy, EStimEnabledFieldLegacy, \
    SampleLengthField, IsRemovedTrialField, IsTextureSplitField, SplitRenderIsSampleField, InvertedShadingField, \
    ContrastTextureField, Is3DChoiceField, CoherenceField
from src.analysis.nafc.psychometric_curves import collect_choice_trials


def compile_latest(exp_conn, trial_tstamps=None):
    """Compile choice trials into the EStimShapeTrials column format.

    trial_tstamps: optional list of trial timestamps (When) to compile. When None, every
    choice trial since 2024-07-10 is compiled (the batch default). The live GUI passes a
    subset so only newly-completed trials are (re)compiled."""
    if trial_tstamps is None:
        since_date = time_util.from_date_to_now(2024, 7, 10)
        trial_tstamps = collect_choice_trials(exp_conn, since_date)

    fields = CachedFieldList()
    fields.append(StimSpecIdField(exp_conn))
    fields.append(IsCorrectField(exp_conn))
    fields.append(IsHypothesizedField(exp_conn))
    fields.append(NoiseChanceField(exp_conn))
    fields.append(NumRandDistractorsField(exp_conn))
    fields.append(NumChoicesField(exp_conn))
    fields.append(NumProceduralDistractorsField(exp_conn))
    fields.append(StimTypeField(exp_conn))
    fields.append(ChoiceField(exp_conn))
    fields.append(GenIdField(exp_conn))
    fields.append(EStimEnabledField(exp_conn))
    fields.append(EStimSpecIdField(exp_conn))
    fields.append(BaseMStickIdField(exp_conn))
    fields.append(PickedBaseMStickIdField(exp_conn))
    fields.append(IsDeltaField(exp_conn))
    fields.append(IsRemovedTrialField(exp_conn))
    fields.append(EStimPolarityField(exp_conn))
    fields.append(ChoiceField(exp_conn))
    fields.append(SampleLengthField(exp_conn))
    # Split-texture (EStimShapeSplitTextureNAFCStim) trial info; None/NaN for other trial types.
    fields.append(IsTextureSplitField(exp_conn))
    fields.append(SplitRenderIsSampleField(exp_conn))
    fields.append(InvertedShadingField(exp_conn))
    fields.append(ContrastTextureField(exp_conn))
    fields.append(Is3DChoiceField(exp_conn))
    fields.append(CoherenceField(exp_conn))

    data = fields.to_data(trial_tstamps)
    if 'TrialStartStop' in data.columns:
        data['trial_start'] = data['TrialStartStop'].apply(lambda x: x.start if x is not None else None)
        data['trial_end'] = data['TrialStartStop'].apply(lambda x: x.stop if x is not None else None)
        data = data.drop(columns=['TrialStartStop'])

    if 'IsDelta' in data.columns:
        data['trial_type'] = data['IsDelta'].apply(lambda x: "Hypothesized Shape" if not x else "Delta Shape")
    if 'IsRemovedTrial' in data.columns:
        data['trial_type'] = data.apply(lambda row: "Removed Trial" if row['IsRemovedTrial'] else row.get('trial_type', None), axis=1)

    # if trial class is EStimShapeProceduralBehavioralStim then trial_type is behavioral
    data['trial_type'] = data.apply(lambda row: "Behavioral" if row['StimType'] == 'EStimShapeProceduralBehavioralStim' else row.get('trial_type', None), axis=1)

    data = data.rename(columns={
        'StimSpecId' : 'task_id',
        'StimType': 'trial_class',
        'EStimEnabled': 'is_estim_on',
        'IsCorrect': 'is_correct_choice',
        'IsHypothesized': 'is_hypothesized_choice',
        'EStimSpecId': 'estim_spec_id',
        'NoiseChance': 'noise_chance',
        'NumRandDistractors': 'num_rand_distractors',
        'NumChoices': 'num_choices',
        'NumProceduralDistractors': 'num_procedural_distractors',
        'BaseMStickId': 'base_mstick_id',
        'PickedBaseMStickId': 'picked_base_mstick_id',
        'GenId': 'gen_id',
        'SampleLength': 'sample_length',
        'IsTextureSplit': 'is_texture_split',
        'SplitRenderIsSample': 'split_render_is_sample',
        'InvertedShading': 'inverted_shading',
        'ContrastTexture': 'contrast_texture',
        'Is3DChoice': 'is_3d_choice',
        'Coherence': 'coherence',
    })
    return data



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
    max_gen_id = 7
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
