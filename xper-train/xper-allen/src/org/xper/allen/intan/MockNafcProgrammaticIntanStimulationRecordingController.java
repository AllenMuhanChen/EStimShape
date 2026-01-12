package org.xper.allen.intan;

import org.xper.classic.vo.TrialContext;
import org.xper.intan.stimulation.*;
import org.xper.rfplot.gui.CyclicIterator;

import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.Map;

public class MockNafcProgrammaticIntanStimulationRecordingController extends NAFCProgrammaticDigitalTriggerIntanStimulationRecordingController{

    private static CyclicIterator<RHSChannel> channels;

    static{
        Collection<RHSChannel> chanList = new ArrayList<RHSChannel>();
        chanList.add(RHSChannel.A007);
        chanList.add(RHSChannel.A008);
        chanList.add(RHSChannel.A025);
        channels = new CyclicIterator<>(chanList);
    }
    @Override
    protected String getEStimSpec(TrialContext context) {
        Map<RHSChannel, ChannelEStimParameters> parametersForChannels = new LinkedHashMap<>();
        WaveformParameters waveformParameters = new WaveformParameters(
                StimulationShape.Biphasic,
                StimulationPolarity.NegativeFirst,
                5000.0,
                5000.0,
                1000.0,
                50.0,
                50.0
        );

        PulseTrainParameters pulseTrainParameters = new PulseTrainParameters(
                PulseRepetition.SinglePulse,
                1,
                10.0,
                4000,
                TriggerEdgeOrLevel.Level,
                0.0);

        AmpSettleParameters ampSettleParameters = new AmpSettleParameters(
                true,
                0.0,
                2000,
                true
        );

        ChargeRecoveryParameters chargeRecoveryParameters = new ChargeRecoveryParameters(
                true,
                100.0,
                1000.0
        );

        ChannelEStimParameters channelEStimParameters = new ChannelEStimParameters(
                waveformParameters,
                pulseTrainParameters,
                ampSettleParameters,
                chargeRecoveryParameters);
        parametersForChannels.put(channels.next(), channelEStimParameters);
        EStimParameters eStimParameters = new EStimParameters(parametersForChannels);
        return eStimParameters.toXml();
    }
}
