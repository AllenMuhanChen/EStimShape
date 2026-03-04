package org.xper.intan.stimulation;

import junit.framework.TestCase;

import java.util.HashMap;
import java.util.Map;

public class EStimParametersTest extends TestCase {

    private EStimParameters original;

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

        AmpSettleParameters ampSettle = new AmpSettleParameters(
                true, 0.0, 1000.0, false
        );

        ChargeRecoveryParameters chargeRecovery = new ChargeRecoveryParameters(
                true, 100.0, 500.0
        );

        ChannelEStimParameters channelParams = new ChannelEStimParameters(
                waveform, pulseTrain, ampSettle, chargeRecovery
        );

        Map<RHSChannel, ChannelEStimParameters> channelMap = new HashMap<>();
        channelMap.put(RHSChannel.A005, channelParams);
        channelMap.put(RHSChannel.A010, new ChannelEStimParameters(
                new WaveformParameters(StimulationShape.Triphasic, StimulationPolarity.PositiveFirst,
                        300.0, 300.0, 50.0, 20.0, 20.0),
                new PulseTrainParameters(PulseRepetition.SinglePulse, 1, 10000.0, 500.0,
                        TriggerEdgeOrLevel.Level, 100.0),
                new AmpSettleParameters(false, 10.0, 2000.0, true),
                new ChargeRecoveryParameters(false, 0.0, 0.0)
        ));

        original = new EStimParameters(channelMap);
    }

    public void testXmlRoundTrip() {
        String xml = original.toXml();
        EStimParameters deserialized = EStimParameters.fromXml(xml);

        assertChannelMapEquals(original, deserialized);
    }

    public void testXmlContainsNoReferences() {
        String xml = original.toXml();
        assertFalse("XML should not contain reference attributes",
                xml.contains("reference="));
    }

    public void testXmlRoundTripAfterDeepCopy() {
        EStimParameters copy = new EStimParameters(original);
        String xml = copy.toXml();
        EStimParameters deserialized = EStimParameters.fromXml(xml);

        assertChannelMapEquals(original, deserialized);
    }

    public void testConstructorEnforcesDeepCopy() {
        WaveformParameters waveform = new WaveformParameters(
                StimulationShape.Biphasic, StimulationPolarity.NegativeFirst,
                200.0, 200.0, 100.0, 10.0, 10.0
        );
        PulseTrainParameters pulseTrain = new PulseTrainParameters(
                PulseRepetition.PulseTrain, 5, 10000.0, 1000.0,
                TriggerEdgeOrLevel.Edge, 0.0
        );
        ChannelEStimParameters channelParams = new ChannelEStimParameters(
                waveform, pulseTrain, new AmpSettleParameters(), new ChargeRecoveryParameters()
        );

        Map<RHSChannel, ChannelEStimParameters> inputMap = new HashMap<>();
        inputMap.put(RHSChannel.A000, channelParams);

        EStimParameters eStim = new EStimParameters(inputMap);

        // The stored object should not be the same instance as what was passed in
        ChannelEStimParameters stored = eStim.geteStimParametersForChannels().get(RHSChannel.A000);
        assertNotSame(channelParams, stored);
        assertNotSame(channelParams.getWaveformParameters(), stored.getWaveformParameters());
        assertNotSame(channelParams.getPulseTrainParameters(), stored.getPulseTrainParameters());
        assertNotSame(channelParams.getAmpSettleParameters(), stored.getAmpSettleParameters());
        assertNotSame(channelParams.getChargeRecoveryParameters(), stored.getChargeRecoveryParameters());

        // But values should be equal
        assertWaveformEquals(channelParams.getWaveformParameters(), stored.getWaveformParameters());

        // Mutating the original should not affect the stored copy
        waveform.setA1(999.0);
        assertEquals(10.0, stored.getWaveformParameters().getA1());
    }

    public void testPutEnforcesDeepCopy() {
        WaveformParameters waveform = new WaveformParameters(
                StimulationShape.Biphasic, StimulationPolarity.NegativeFirst,
                200.0, 200.0, 100.0, 10.0, 10.0
        );
        ChannelEStimParameters channelParams = new ChannelEStimParameters(
                waveform,
                new PulseTrainParameters(PulseRepetition.PulseTrain, 5, 10000.0, 1000.0,
                        TriggerEdgeOrLevel.Edge, 0.0),
                new AmpSettleParameters(),
                new ChargeRecoveryParameters()
        );

        EStimParameters eStim = new EStimParameters();
        eStim.put(RHSChannel.A000, channelParams);

        ChannelEStimParameters stored = eStim.geteStimParametersForChannels().get(RHSChannel.A000);
        assertNotSame(channelParams, stored);

        // Mutating the original should not affect the stored copy
        waveform.setA1(999.0);
        assertEquals(10.0, stored.getWaveformParameters().getA1());
    }

    public void testGetterReturnsImmutableMap() {
        Map<RHSChannel, ChannelEStimParameters> returned = original.geteStimParametersForChannels();

        try {
            returned.put(RHSChannel.A000, new ChannelEStimParameters());
            fail("Expected UnsupportedOperationException");
        } catch (UnsupportedOperationException e) {
            // expected
        }

        try {
            returned.remove(RHSChannel.A005);
            fail("Expected UnsupportedOperationException");
        } catch (UnsupportedOperationException e) {
            // expected
        }

        try {
            returned.clear();
            fail("Expected UnsupportedOperationException");
        } catch (UnsupportedOperationException e) {
            // expected
        }
    }

    private void assertChannelMapEquals(EStimParameters expected, EStimParameters actual) {
        Map<RHSChannel, ChannelEStimParameters> expectedMap = expected.geteStimParametersForChannels();
        Map<RHSChannel, ChannelEStimParameters> actualMap = actual.geteStimParametersForChannels();

        assertEquals(expectedMap.size(), actualMap.size());

        for (RHSChannel channel : expectedMap.keySet()) {
            assertTrue("Missing channel: " + channel, actualMap.containsKey(channel));

            ChannelEStimParameters expectedParams = expectedMap.get(channel);
            ChannelEStimParameters actualParams = actualMap.get(channel);

            assertWaveformEquals(expectedParams.getWaveformParameters(), actualParams.getWaveformParameters());
            assertPulseTrainEquals(expectedParams.getPulseTrainParameters(), actualParams.getPulseTrainParameters());
            assertAmpSettleEquals(expectedParams.getAmpSettleParameters(), actualParams.getAmpSettleParameters());
            assertChargeRecoveryEquals(expectedParams.getChargeRecoveryParameters(), actualParams.getChargeRecoveryParameters());
        }
    }

    private void assertWaveformEquals(WaveformParameters expected, WaveformParameters actual) {
        assertEquals(expected.getShape(), actual.getShape());
        assertEquals(expected.getPolarity(), actual.getPolarity());
        assertEquals(expected.getD1(), actual.getD1());
        assertEquals(expected.getD2(), actual.getD2());
        assertEquals(expected.getDp(), actual.getDp());
        assertEquals(expected.getA1(), actual.getA1());
        assertEquals(expected.getA2(), actual.getA2());
    }

    private void assertPulseTrainEquals(PulseTrainParameters expected, PulseTrainParameters actual) {
        assertEquals(expected.getPulseRepetition(), actual.getPulseRepetition());
        assertEquals(expected.getNumRepetitions(), actual.getNumRepetitions());
        assertEquals(expected.getPulseTrainPeriod(), actual.getPulseTrainPeriod());
        assertEquals(expected.getPostStimRefractoryPeriod(), actual.getPostStimRefractoryPeriod());
        assertEquals(expected.getTriggerEdgeOrLevel(), actual.getTriggerEdgeOrLevel());
        assertEquals(expected.getPostTriggerDelay(), actual.getPostTriggerDelay());
    }

    private void assertAmpSettleEquals(AmpSettleParameters expected, AmpSettleParameters actual) {
        assertEquals(expected.getEnableAmpSettle(), actual.getEnableAmpSettle());
        assertEquals(expected.getPreStimAmpSettle(), actual.getPreStimAmpSettle());
        assertEquals(expected.getPostStimAmpSettle(), actual.getPostStimAmpSettle());
        assertEquals(expected.getMaintainAmpSettleDuringPulseTrain(), actual.getMaintainAmpSettleDuringPulseTrain());
    }

    private void assertChargeRecoveryEquals(ChargeRecoveryParameters expected, ChargeRecoveryParameters actual) {
        assertEquals(expected.getEnableChargeRecovery(), actual.getEnableChargeRecovery());
        assertEquals(expected.getPostStimChargeRecoveryOn(), actual.getPostStimChargeRecoveryOn());
        assertEquals(expected.getPostStimChargeRecoveryOff(), actual.getPostStimChargeRecoveryOff());
    }
}