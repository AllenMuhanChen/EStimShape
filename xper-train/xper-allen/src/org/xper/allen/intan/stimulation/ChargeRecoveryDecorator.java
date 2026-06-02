package org.xper.allen.intan.stimulation;

import org.xper.intan.stimulation.*;

public class ChargeRecoveryDecorator {

    private final GroundMode groundMode;

    public ChargeRecoveryDecorator() {
        this(GroundMode.PostTrain);
    }

    public ChargeRecoveryDecorator(GroundMode groundMode) {
        this.groundMode = groundMode;
    }

    public EStimParameters decorate(EStimParameters inputParameters) {

        ChannelEStimParameters modelParam = inputParameters.geteStimParametersForChannels().values().iterator().next();
        WaveformParameters modelWaveform = modelParam.getWaveformParameters();

        // Zero-amplitude waveform with same timing as the stim waveform
        StimulationShape shape = modelWaveform.getShape();
        double d1 = modelWaveform.getD1();
        double d2 = modelWaveform.getD2();
        double dp = modelWaveform.getDp();
        WaveformParameters groundWaveFormParameters = new WaveformParameters(
                shape, StimulationPolarity.PositiveFirst, d1, d2, dp, 0.0, 0.0);

        PulseTrainParameters groundPulseTrainParameters = buildGroundPulseTrain(modelParam, d1, d2, dp);
        ChargeRecoveryParameters groundChargeRecoveryParameters = new ChargeRecoveryParameters(modelParam.getChargeRecoveryParameters());
        AmpSettleParameters groundChargeAmpSettleParameters = new AmpSettleParameters();

        ChannelEStimParameters groundPulseParameters = new ChannelEStimParameters(
                groundWaveFormParameters,
                groundPulseTrainParameters,
                groundChargeAmpSettleParameters,
                groundChargeRecoveryParameters
        );

        EStimParameters outputParameters = new EStimParameters(inputParameters);
        // TODO: don't hardcode port "A"
        for (RHSChannel channel : RHSChannel.getChannelsForPort("A")){
            if (!outputParameters.geteStimParametersForChannels().containsKey(channel)){
                outputParameters.put(channel, new ChannelEStimParameters(groundPulseParameters));
            }
        }
        return outputParameters;
    }

    /**
     * Build the pulse-train config for ground-only channels based on groundMode.
     *
     * PostTrain: clone the stim channel's pulse train exactly. Ground pulses fire
     * cycle-for-cycle with stim pulses; charge recovery happens after the train.
     *
     * BetweenPulse: Level + SinglePulse so each held-high tick fires one ground
     * pulse. refractoryPeriod is set to leave room for one stim pulse worth of
     * waveform between ground pulses, matching the stim cadence so ground pulses
     * land between stim pulses when both share the same held trigger window.
     */
    private PulseTrainParameters buildGroundPulseTrain(ChannelEStimParameters modelParam, double d1, double d2, double dp) {
        PulseTrainParameters stimTrain = modelParam.getPulseTrainParameters();
        if (groundMode == GroundMode.PostTrain) {
            return new PulseTrainParameters(stimTrain);
        }
        // BetweenPulse: Level + SinglePulse
        double pulseWidth = d1 + d2 + dp;
        double refractory = stimTrain.getPulseTrainPeriod() - pulseWidth;
        if (refractory < 0) {
            refractory = 0;
        }
        return new PulseTrainParameters(
                PulseRepetition.SinglePulse,
                1,
                stimTrain.getPulseTrainPeriod(),
                refractory,
                TriggerEdgeOrLevel.Level,
                stimTrain.getPostTriggerDelay()
        );
    }

    public GroundMode getGroundMode() {
        return groundMode;
    }
}
