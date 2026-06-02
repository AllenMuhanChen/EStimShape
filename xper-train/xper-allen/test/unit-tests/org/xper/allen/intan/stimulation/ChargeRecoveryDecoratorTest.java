package org.xper.allen.intan.stimulation;

import junit.framework.TestCase;
import org.xper.intan.stimulation.*;

public class ChargeRecoveryDecoratorTest extends TestCase {

    private EStimParameters inputParameters;

    public void setUp() throws Exception {
        super.setUp();

        WaveformParameters waveform = new WaveformParameters(
                StimulationShape.Biphasic,
                StimulationPolarity.NegativeFirst,
                200.0, 200.0, 100.0, 10.0, 10.0
        );

        PulseTrainParameters pulseTrain = new PulseTrainParameters(
                PulseRepetition.PulseTrain,
                5,
                10000.0,
                1000.0,
                TriggerEdgeOrLevel.Edge,
                0.0
        );

        AmpSettleParameters ampSettle = new AmpSettleParameters(true, 0.0, 1000.0, false);
        ChargeRecoveryParameters chargeRecovery = new ChargeRecoveryParameters(true, 100.0, 500.0);

        inputParameters = new EStimParameters();
        ChannelEStimParameters pulse = new ChannelEStimParameters(waveform, pulseTrain, ampSettle, chargeRecovery);
        inputParameters.put(RHSChannel.A005, pulse);
        inputParameters.put(RHSChannel.A010, pulse);
        inputParameters.put(RHSChannel.A020, pulse);
    }

    public void testDecorate_postTrain_groundChannelsMirrorStimTrain() {
        ChargeRecoveryDecorator decorator = new ChargeRecoveryDecorator(GroundMode.PostTrain);
        EStimParameters result = decorator.decorate(inputParameters);

        for (RHSChannel channel : RHSChannel.getChannelsForPort("A")) {
            assertTrue("Missing channel: " + channel,
                    result.geteStimParametersForChannels().containsKey(channel));
        }

        for (RHSChannel stimChannel : new RHSChannel[]{RHSChannel.A005, RHSChannel.A010, RHSChannel.A020}) {
            ChannelEStimParameters params = result.geteStimParametersForChannels().get(stimChannel);
            assertEquals(10.0, params.getWaveformParameters().getA1());
            assertEquals(10.0, params.getWaveformParameters().getA2());
        }

        ChannelEStimParameters groundParams = result.geteStimParametersForChannels().get(RHSChannel.A000);
        WaveformParameters wf = groundParams.getWaveformParameters();
        assertEquals(0.0, wf.getA1());
        assertEquals(0.0, wf.getA2());
        assertEquals(StimulationShape.Biphasic, wf.getShape());
        assertEquals(200.0, wf.getD1());

        PulseTrainParameters pt = groundParams.getPulseTrainParameters();
        assertEquals(TriggerEdgeOrLevel.Edge, pt.getTriggerEdgeOrLevel());
        assertEquals(PulseRepetition.PulseTrain, pt.getPulseRepetition());
        assertEquals(5, pt.getNumRepetitions());
        assertEquals(10000.0, pt.getPulseTrainPeriod());

        ChargeRecoveryParameters cr = groundParams.getChargeRecoveryParameters();
        assertTrue(cr.getEnableChargeRecovery());
        assertEquals(100.0, cr.getPostStimChargeRecoveryOn());
        assertEquals(500.0, cr.getPostStimChargeRecoveryOff());
    }

    public void testDecorate_betweenPulse_groundChannelsUseLevelSinglePulse() {
        ChargeRecoveryDecorator decorator = new ChargeRecoveryDecorator(GroundMode.BetweenPulse);
        EStimParameters result = decorator.decorate(inputParameters);

        ChannelEStimParameters groundParams = result.geteStimParametersForChannels().get(RHSChannel.A000);
        PulseTrainParameters pt = groundParams.getPulseTrainParameters();
        assertEquals(TriggerEdgeOrLevel.Level, pt.getTriggerEdgeOrLevel());
        assertEquals(PulseRepetition.SinglePulse, pt.getPulseRepetition());
        // refractory = trainPeriod - (d1+d2+dp) = 10000 - 500 = 9500
        assertEquals(9500.0, pt.getPostStimRefractoryPeriod());

        // Stim channels themselves should be untouched
        ChannelEStimParameters stimParams = result.geteStimParametersForChannels().get(RHSChannel.A005);
        assertEquals(TriggerEdgeOrLevel.Edge, stimParams.getPulseTrainParameters().getTriggerEdgeOrLevel());
        assertEquals(10.0, stimParams.getWaveformParameters().getA1());
    }

    public void testDecorate_defaultIsPostTrain() {
        ChargeRecoveryDecorator decorator = new ChargeRecoveryDecorator();
        assertEquals(GroundMode.PostTrain, decorator.getGroundMode());
    }

    public void testDecorateDoesNotMutateInput() {
        int originalSize = inputParameters.geteStimParametersForChannels().size();
        new ChargeRecoveryDecorator().decorate(inputParameters);
        assertEquals(originalSize, inputParameters.geteStimParametersForChannels().size());
    }
}
