package org.xper.allen.intan.stimulation;

import junit.framework.TestCase;
import org.lwjgl.opengl.EXTStencilTwoSide;
import org.xper.intan.stimulation.*;

import java.util.HashMap;
import java.util.Map;

public class ChargeRecoveryDecoratorTest extends TestCase {

    private EStimParameters inputParameters;
    private ChargeRecoveryDecorator decorator;

    public void setUp() throws Exception {
        super.setUp();
        decorator = new ChargeRecoveryDecorator();

        WaveformParameters waveform = new WaveformParameters(
                StimulationShape.Biphasic,
                StimulationPolarity.NegativeFirst,
                200.0,  // d1
                200.0,  // d2
                100.0,   // dp
                10.0,   // a1
                10.0    // a2
        );

        PulseTrainParameters pulseTrain = new PulseTrainParameters(
                PulseRepetition.PulseTrain,
                5,        // numRepetitions
                10000.0,  // pulseTrainPeriod
                1000.0,   // postStimRefractoryPeriod
                TriggerEdgeOrLevel.Edge,
                0.0       // postTriggerDelay
        );

        AmpSettleParameters ampSettle = new AmpSettleParameters(
                true, 0.0, 1000.0, false
        );

        ChargeRecoveryParameters chargeRecovery = new ChargeRecoveryParameters(
                true, 100.0, 500.0
        );

        inputParameters = new EStimParameters();
        ChannelEStimParameters pulse = new ChannelEStimParameters(waveform, pulseTrain, ampSettle, chargeRecovery);
        inputParameters.put(RHSChannel.A005, pulse);
        inputParameters.put(RHSChannel.A010, pulse);
        inputParameters.put(RHSChannel.A020, pulse);
    }

    public void testDecorate() {
        EStimParameters result = decorator.decorate(inputParameters);

        // All 32 port A channels should be present
        for (RHSChannel channel : RHSChannel.getChannelsForPort("A")) {
            assertTrue("Missing channel: " + channel,
                    result.geteStimParametersForChannels().containsKey(channel));
        }

        // Original stim channels should retain nonzero amplitudes
        for (RHSChannel stimChannel : new RHSChannel[]{RHSChannel.A005, RHSChannel.A010, RHSChannel.A020}) {
            ChannelEStimParameters params = result.geteStimParametersForChannels().get(stimChannel);
            assertEquals(10.0, params.getWaveformParameters().getA1());
            assertEquals(10.0, params.getWaveformParameters().getA2());
        }

        // Non-stim channels should have zero-amplitude ground pulses
        for (RHSChannel channel : RHSChannel.getChannelsForPort("A")) {
            if (channel == RHSChannel.A005 || channel == RHSChannel.A010 || channel == RHSChannel.A020) {
                continue;
            }
            ChannelEStimParameters params = result.geteStimParametersForChannels().get(channel);
            WaveformParameters wf = params.getWaveformParameters();
            assertEquals(0.0, wf.getA1());
            assertEquals(0.0, wf.getA2());

            // Shape and durations should match the model
            assertEquals(StimulationShape.Biphasic, wf.getShape());
            assertEquals(200.0, wf.getD1());
            assertEquals(200.0, wf.getD2());

            // Charge recovery should be copied from model
            ChargeRecoveryParameters cr = params.getChargeRecoveryParameters();
            assertTrue(cr.getEnableChargeRecovery());
            assertEquals(100.0, cr.getPostStimChargeRecoveryOn());
            assertEquals(500.0, cr.getPostStimChargeRecoveryOff());

            System.out.println(result.toXml());
        }
    }

    public void testDecorateDoesNotMutateInput() {
        int originalSize = inputParameters.geteStimParametersForChannels().size();
        decorator.decorate(inputParameters);
        assertEquals(originalSize, inputParameters.geteStimParametersForChannels().size());
    }
}