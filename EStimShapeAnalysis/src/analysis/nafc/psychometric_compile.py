from clat.util.connection import Connection
from src.analysis.nafc.psychometric_compile_for_sessions import compile_260120_0, compile_260115_0, compile_260113_0, \
    compile_260107_0, compile_251231_0, compile_251226_0, compile_260108_0
from src.repository.export_to_repository import read_session_id_from_db_name
from src.startup import context
import xml.etree.ElementTree as ET


def main():
    # Database connections
    exp_conn = Connection(context.nafc_database)
    ga_conn = Connection(context.ga_database)

    create_estim_obj_data_table()
    export_estim_parameters(exp_conn)
    create_estimshape_trials_table()

    session_id, _ = read_session_id_from_db_name(context.nafc_database)
    compile_and_export_to_repo(exp_conn, session_id)


def export_to_repo(session_id, data):
    """
    Export dataframe to EStimShapeTrials table

    Args:
        session_id: Session identifier
        data: Pandas dataframe with trial data (columns already renamed to match DB schema)
    """
    if data is None or len(data) == 0:
        print(f"No data to export for session {session_id}")
        return

    repo_conn = Connection("allen_data_repository")

    # Add session_id to every row
    data = data.copy()
    data['session_id'] = session_id

    # Define expected table columns
    table_columns = [
        'session_id', 'task_id', 'estim_spec_id', 'is_estim_on',
        'is_hypothesized_choice', 'is_correct_choice', 'trial_type',
        'noise_chance', 'base_mstick_id', 'gen_id', 'trial_start', 'trial_end'
    ]

    # Find which columns we have in the dataframe
    columns_to_insert = [col for col in table_columns if col in data.columns]

    if 'task_id' not in columns_to_insert:
        print(f"Error: task_id column missing from data")
        return

    # Build INSERT query
    placeholders = ', '.join(['%s'] * len(columns_to_insert))
    column_names = ', '.join(columns_to_insert)

    insert_query = f"""
        INSERT IGNORE INTO EStimShapeTrials ({column_names})
        VALUES ({placeholders})
    """

    # Insert each row
    inserted_count = 0
    for _, row in data.iterrows():
        values = tuple(row[col] if col in row.index else None for col in columns_to_insert)
        repo_conn.execute(insert_query, values)
        inserted_count += 1

    print(f"Exported {inserted_count} trials for session {session_id} to EStimShapeTrials")


def compile_and_export_to_repo(exp_conn, session_id: str):
    data = None
    if session_id == "260120_0":
        data = compile_260120_0(exp_conn)
    elif session_id == "260115_0":
        data = compile_260115_0(exp_conn)
    elif session_id == "260113_0":
        data = compile_260113_0(exp_conn)
    elif session_id == "260108_0":
        data = compile_260108_0(exp_conn)
    elif session_id == "260107_0":
        data = compile_260107_0(exp_conn)
    elif session_id == "251231_0":
        data = compile_251231_0(exp_conn)
    elif session_id == "251226_0":
        data = compile_251226_0(exp_conn)
    # EARLIER than this and we don't have our new GA based shape production
    export_to_repo(session_id, data)


def create_estimshape_trials_table():
    conn = Connection("allen_data_repository")

    # Create EStimParameters table
    conn.execute("""
                 CREATE TABLE IF NOT EXISTS EStimShapeTrials
                 (
                     session_id                             VARCHAR(10) NOT NULL,
                     task_id                                BIGINT      NOT NULL,
                     
                     estim_spec_id                          BIGINT,      
                     is_estim_on                            BOOLEAN     NOT NULL,
                     is_hypothesized_choice                 BOOLEAN     NOT NULL,
                     is_correct_choice                      BOOLEAN     NOT NULL,
                     trial_type                             VARCHAR(20) NOT NULL,
                     noise_chance                           FLOAT       NOT NULL,

                     PRIMARY KEY (task_id),
                     FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
                 ) ENGINE = InnoDB
                   DEFAULT CHARSET = latin1
                 """)

    try:
        conn.execute("""
                     ALTER TABLE EStimShapeTrials
                         ADD COLUMN base_mstick_id          BIGINT,
                         ADD COLUMN gen_id                  INTEGER,
                         ADD COLUMN trial_start             BIGINT,
                         ADD COLUMN trial_end               BIGINT
                     """)
    except:
        # Columns already exist, ignore the error
        pass

def export_estim_parameters(exp_conn):
    session_id, _ = read_session_id_from_db_name(context.nafc_database)
    repo_conn = Connection("allen_data_repository")

    # Read all unique EStim specs from exp database
    exp_conn.execute("""
                     SELECT DISTINCT id, spec
                     FROM EStimObjData
                     WHERE spec IS NOT NULL
                     ORDER BY id
                     """)
    result = exp_conn.fetch_all()

    for row in result:
        estim_spec_id = row[0]
        if estim_spec_id > 1000:
            continue
        spec_xml = row[1]

        # Parse the XML
        root = ET.fromstring(spec_xml)

        # Collect all entries first
        entries = root.findall('.//eStimParametersForChannels/entry')

        # Store the first full set of parameters for reference
        reference_params = None

        for entry in entries:
            channel_elem = entry.find('org.xper.intan.stimulation.RHSChannel')
            if channel_elem is None:
                continue
            channel = channel_elem.text

            channel_params_elem = entry.find('org.xper.intan.stimulation.ChannelEStimParameters')
            if channel_params_elem is None:
                continue

            # Check if this entire element is a reference
            if channel_params_elem.get('reference') is not None:
                # This channel references the first full entry
                if reference_params is None:
                    print(f"Warning: Found reference before any full parameters for channel {channel}")
                    continue
                params = reference_params.copy()
            else:
                # Parse the full parameters
                params = extract_channel_parameters(channel_params_elem)
                # Store as reference for future channels if this is the first one
                if reference_params is None:
                    reference_params = params.copy()

            # Insert into database
            insert_estim_parameters(repo_conn, session_id, estim_spec_id, channel, params)

    print(f"Exported EStim parameters for session {session_id}")


def extract_channel_parameters(channel_elem):
    """Extract parameters from XML element"""
    params = {}

    # WaveformParameters
    wf = channel_elem.find('waveformParameters')
    if wf is not None:
        params['waveform'] = {
            'shape': get_text(wf, 'shape'),
            'polarity': get_text(wf, 'polarity'),
            'd1': get_float(wf, 'd1'),
            'd2': get_float(wf, 'd2'),
            'dp': get_float(wf, 'dp'),
            'a1': get_float(wf, 'a1'),
            'a2': get_float(wf, 'a2')
        }

    # PulseTrainParameters
    pt = channel_elem.find('pulseTrainParameters')
    if pt is not None:
        params['pulse_train'] = {
            'pulse_repetition': get_text(pt, 'pulseRepetition'),
            'num_repetitions': get_int(pt, 'numRepetitions'),
            'pulse_train_period': get_float(pt, 'pulseTrainPeriod'),
            'post_stim_refractory_period': get_float(pt, 'postStimRefractoryPeriod'),
            'trigger_edge_or_level': get_text(pt, 'triggerEdgeOrLevel'),
            'post_trigger_delay': get_float(pt, 'postTriggerDelay')
        }

    # AmpSettleParameters
    amp = channel_elem.find('ampSettleParameters')
    if amp is not None:
        params['amp_settle'] = {
            'enable_amp_settle': get_bool(amp, 'enableAmpSettle'),
            'pre_stim_amp_settle': get_float(amp, 'preStimAmpSettle'),
            'post_stim_amp_settle': get_float(amp, 'postStimAmpSettle'),
            'maintain_amp_settle_during_pulse_train': get_bool(amp, 'maintainAmpSettleDuringPulseTrain')
        }

    # ChargeRecoveryParameters
    cr = channel_elem.find('chargeRecoveryParameters')
    if cr is not None:
        params['charge_recovery'] = {
            'enable_charge_recovery': get_bool(cr, 'enableChargeRecovery'),
            'post_stim_charge_recovery_on': get_float(cr, 'postStimChargeRecoveryOn'),
            'post_stim_charge_recovery_off': get_float(cr, 'postStimChargeRecoveryOff')
        }

    return params


def get_text(elem, tag):
    """Get text content of a child element"""
    child = elem.find(tag)
    return child.text if child is not None else None


def get_float(elem, tag):
    """Get float value from a child element"""
    text = get_text(elem, tag)
    return float(text) if text else None


def get_int(elem, tag):
    """Get int value from a child element"""
    text = get_text(elem, tag)
    return int(text) if text else None


def get_bool(elem, tag):
    """Get boolean value from a child element"""
    text = get_text(elem, tag)
    return text == 'true' if text else None


def insert_estim_parameters(conn, session_id, estim_spec_id, channel, params):
    """Insert parameters for one channel into the database"""
    wf = params.get('waveform', {})
    pt = params.get('pulse_train', {})
    amp = params.get('amp_settle', {})
    cr = params.get('charge_recovery', {})

    conn.execute("""
                 INSERT IGNORE INTO EStimParameters (session_id, estim_spec_id, channel,
                                              shape, polarity, d1, d2, dp, a1, a2,
                                              pulse_repetition, num_repetitions, pulse_train_period,
                                              post_stim_refractory_period, trigger_edge_or_level, post_trigger_delay,
                                              enable_amp_settle, pre_stim_amp_settle, post_stim_amp_settle,
                                              maintain_amp_settle_during_pulse_train,
                                              enable_charge_recovery, post_stim_charge_recovery_on,
                                              post_stim_charge_recovery_off)
                 VALUES (%s, %s, %s,
                         %s, %s, %s, %s, %s, %s, %s,
                         %s, %s, %s, %s, %s, %s,
                         %s, %s, %s, %s,
                         %s, %s, %s)
                 """, (
                     session_id, estim_spec_id, channel,
                     wf.get('shape'), wf.get('polarity'), wf.get('d1'), wf.get('d2'),
                     wf.get('dp'), wf.get('a1'), wf.get('a2'),
                     pt.get('pulse_repetition'), pt.get('num_repetitions'), pt.get('pulse_train_period'),
                     pt.get('post_stim_refractory_period'), pt.get('trigger_edge_or_level'),
                     pt.get('post_trigger_delay'),
                     amp.get('enable_amp_settle'), amp.get('pre_stim_amp_settle'),
                     amp.get('post_stim_amp_settle'), amp.get('maintain_amp_settle_during_pulse_train'),
                     cr.get('enable_charge_recovery'), cr.get('post_stim_charge_recovery_on'),
                     cr.get('post_stim_charge_recovery_off')
                 ))


def create_estim_obj_data_table():
    conn = Connection("allen_data_repository")

    # Create EStimParameters table
    conn.execute("""
                 CREATE TABLE IF NOT EXISTS EStimParameters
                 (
                     session_id                             VARCHAR(10) NOT NULL,
                     estim_spec_id                          BIGINT      NOT NULL,
                     channel                                VARCHAR(4)  NOT NULL,

                     -- WaveformParameters
                     shape                                  ENUM ('Biphasic', 'BiphasicWithInterphaseDelay', 'Triphasic'),
                     polarity                               ENUM ('NegativeFirst', 'PositiveFirst'),
                     d1                                     DOUBLE,
                     d2                                     DOUBLE,
                     dp                                     DOUBLE,
                     a1                                     DOUBLE,
                     a2                                     DOUBLE,

                     -- PulseTrainParameters
                     pulse_repetition                       ENUM ('SinglePulse', 'PulseTrain'),
                     num_repetitions                        INT,
                     pulse_train_period                     DOUBLE,
                     post_stim_refractory_period            DOUBLE,
                     trigger_edge_or_level                  ENUM ('Edge', 'Level'),
                     post_trigger_delay                     DOUBLE,

                     -- AmpSettleParameters
                     enable_amp_settle                      BOOLEAN,
                     pre_stim_amp_settle                    DOUBLE,
                     post_stim_amp_settle                   DOUBLE,
                     maintain_amp_settle_during_pulse_train BOOLEAN,

                     -- ChargeRecoveryParameters
                     enable_charge_recovery                 BOOLEAN,
                     post_stim_charge_recovery_on           DOUBLE,
                     post_stim_charge_recovery_off          DOUBLE,

                     PRIMARY KEY (session_id, estim_spec_id, channel),
                     FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
                 ) ENGINE = InnoDB
                   DEFAULT CHARSET = latin1
                 """)

    print("EStimParameters table created successfully")


if __name__ == '__main__':
    main()