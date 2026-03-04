package org.xper.allen.intan.stimulation;

import org.xper.intan.stimulation.*;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class ChargeRecoveryDecorator {


    public EStimParameters decorate(EStimParameters inputParameters) {


        ChannelEStimParameters modelParam = inputParameters.geteStimParametersForChannels().values().iterator().next();
        WaveformParameters modelWaveform = modelParam.getWaveformParameters();

        // using a model waveform to generate same waveform but ZERO amplitude.
        StimulationShape shape =  modelWaveform.getShape();
        double d1 = modelWaveform.getD1();
        double d2 = modelWaveform.getD2();
        double dp = modelWaveform.getDp();
        double a1 = 0.0;
        double a2 = 0.0;
        WaveformParameters groundWaveFormParameters = new WaveformParameters(shape, StimulationPolarity.PositiveFirst, d1, d2, dp, a1, a2);
        PulseTrainParameters groundPulseTrainParameters = new PulseTrainParameters(modelParam.getPulseTrainParameters());
        AmpSettleParameters groundChargeAmpSettleParameters = new AmpSettleParameters();

        // this relies on an already calculated charge recovery... and applies it to non-stim channels.
        // maybe we consider changing this to automatic calculation of proper timing from waveform and apply it.
        ChargeRecoveryParameters groundChargeRecoveryParameters = new ChargeRecoveryParameters(modelParam.getChargeRecoveryParameters());

        ChannelEStimParameters groundPulseParameters = new ChannelEStimParameters(
                groundWaveFormParameters,
                groundPulseTrainParameters,
                groundChargeAmpSettleParameters,
                groundChargeRecoveryParameters
        );

        // Make Output Parameters and add ground pulse to channels without EStim already
        EStimParameters outputParameters = new EStimParameters(inputParameters);
        //TODO: make not only rely on "A", and be set by parameters (or auto detect)
        for (RHSChannel channel : RHSChannel.getChannelsForPort("A")){
            if (!outputParameters.geteStimParametersForChannels().containsKey(channel)){
                outputParameters.put(channel, new ChannelEStimParameters(groundPulseParameters));
            }
        }
        return outputParameters;
    }
}
