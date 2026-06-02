package org.xper.allen.app.estimshape;

import junit.framework.TestCase;
import org.xper.allen.intan.stimulation.EStimParamParser;
import org.xper.intan.stimulation.*;

import java.util.List;
import java.util.Map;

public class EStimSpecWriterTest extends TestCase {

    private EStimParamParser parser;

    public void setUp() throws Exception {
        super.setUp();
        parser = new EStimParamParser();
    }

    public void testChannelsOnly_usesAllDefaults() {
        Map<String, Object> parsed = parser.parse("channels=[\"A025\",\"A030\"]");

        List<RHSChannel> channels = EStimSpecWriter.parseChannels(parsed);
        assertEquals(2, channels.size());
        assertEquals(RHSChannel.A025, channels.get(0));
        assertEquals(RHSChannel.A030, channels.get(1));

        ChannelEStimParameters params = EStimSpecWriter.buildChannelParams(parsed);
        WaveformParameters wf = params.getWaveformParameters();
        assertEquals(StimulationShape.BiphasicWithInterphaseDelay, wf.getShape());
        assertEquals(StimulationPolarity.NegativeFirst, wf.getPolarity());
        assertEquals(200.0, wf.getD1());
        assertEquals(200.0, wf.getD2());
        assertEquals(100.0, wf.getDp());
        assertEquals(2.5, wf.getA1());
        assertEquals(2.5, wf.getA2());

        PulseTrainParameters pt = params.getPulseTrainParameters();
        assertEquals(TriggerEdgeOrLevel.Edge, pt.getTriggerEdgeOrLevel());
        assertEquals(PulseRepetition.PulseTrain, pt.getPulseRepetition());
        // 200 Hz -> 5000 µs period; 200 ms -> 40 pulses
        assertEquals(5000.0, pt.getPulseTrainPeriod());
        assertEquals(40, pt.getNumRepetitions());
        assertEquals(100000.0, pt.getPostTriggerDelay()); // 100 ms in µs
        assertEquals(100000.0, pt.getPostStimRefractoryPeriod()); // 100 ms in µs
    }

    public void testOverrideAmplitudeTuple() {
        Map<String, Object> parsed = parser.parse("channels=[\"A025\"]. a=(3.5,3.5)");

        ChannelEStimParameters params = EStimSpecWriter.buildChannelParams(parsed);
        assertEquals(3.5, params.getWaveformParameters().getA1());
        assertEquals(3.5, params.getWaveformParameters().getA2());
        assertEquals(200.0, params.getWaveformParameters().getD1());
    }

    public void testOverridePolarity() {
        Map<String, Object> parsed = parser.parse("channels=[\"A025\"]. polarity=PositiveFirst");

        ChannelEStimParameters params = EStimSpecWriter.buildChannelParams(parsed);
        assertEquals(StimulationPolarity.PositiveFirst, params.getWaveformParameters().getPolarity());
    }

    public void testFreqAndDuration() {
        Map<String, Object> parsed = parser.parse("channels=[\"A025\"]. freq=100. duration=100");
        ChannelEStimParameters params = EStimSpecWriter.buildChannelParams(parsed);
        PulseTrainParameters pt = params.getPulseTrainParameters();
        // 100 Hz -> 10000 µs period; 100 ms -> 10 pulses
        assertEquals(10000.0, pt.getPulseTrainPeriod());
        assertEquals(10, pt.getNumRepetitions());
    }

    public void testNumPulsesOverride() {
        Map<String, Object> parsed = parser.parse("channels=[\"A025\"]. freq=200. numPulses=5");
        ChannelEStimParameters params = EStimSpecWriter.buildChannelParams(parsed);
        assertEquals(5, params.getPulseTrainParameters().getNumRepetitions());
    }

    public void testDurationExceedsMaxPulsesThrows() {
        // 200 Hz, 256 pulses -> 1280 ms max. 2000 ms should fail.
        Map<String, Object> parsed = parser.parse("channels=[\"A025\"]. freq=200. duration=2000");
        try {
            EStimSpecWriter.buildChannelParams(parsed);
            fail("Expected IllegalArgumentException for duration exceeding max pulses");
        } catch (IllegalArgumentException e) {
            assertTrue(e.getMessage().contains("256"));
        }
    }

    public void testNumPulsesOverrideExceedsMaxThrows() {
        Map<String, Object> parsed = parser.parse("channels=[\"A025\"]. numPulses=300");
        try {
            EStimSpecWriter.buildChannelParams(parsed);
            fail("Expected IllegalArgumentException for numPulses > 256");
        } catch (IllegalArgumentException e) {
            assertTrue(e.getMessage().contains("256"));
        }
    }

    public void testDurationRoundsDownWithWarning() {
        // 200 Hz -> 5000 µs period. 7 ms = 7000 µs = 1.4 pulses -> floor to 1, warn.
        Map<String, Object> parsed = parser.parse("channels=[\"A025\"]. freq=200. duration=7");
        ChannelEStimParameters params = EStimSpecWriter.buildChannelParams(parsed);
        assertEquals(1, params.getPulseTrainParameters().getNumRepetitions());
    }

    public void testTriggerDelayMs() {
        Map<String, Object> parsed = parser.parse("channels=[\"A025\"]. triggerDelayMs=50");
        ChannelEStimParameters params = EStimSpecWriter.buildChannelParams(parsed);
        assertEquals(50000.0, params.getPulseTrainParameters().getPostTriggerDelay());
    }

    public void testTriggerDelayMicrosecondsLegacy() {
        Map<String, Object> parsed = parser.parse("channels=[\"A025\"]. triggerDelay=100");
        ChannelEStimParameters params = EStimSpecWriter.buildChannelParams(parsed);
        assertEquals(100.0, params.getPulseTrainParameters().getPostTriggerDelay());
    }

    public void testTriggerTypeLevel() {
        Map<String, Object> parsed = parser.parse("channels=[\"A025\"]. triggerType=Level");
        ChannelEStimParameters params = EStimSpecWriter.buildChannelParams(parsed);
        assertEquals(TriggerEdgeOrLevel.Level, params.getPulseTrainParameters().getTriggerEdgeOrLevel());
    }

    public void testNoSplits_oneCondition() {
        Map<String, Object> parsed = parser.parse("channels=[\"A025\",\"A030\"]");

        List<EStimParameters> conditions = EStimSpecWriter.buildAllConditions(parsed);
        assertEquals(1, conditions.size());

        Map<RHSChannel, ChannelEStimParameters> map = conditions.get(0).geteStimParametersForChannels();
        assertEquals(2, map.size());
        assertTrue(map.containsKey(RHSChannel.A025));
        assertTrue(map.containsKey(RHSChannel.A030));
    }

    public void testSplitAmplitude_twoConditions() {
        Map<String, Object> parsed = parser.parse(
                "channels=[\"A025\",\"A030\"]. a={(3.5,3.5);(5,5)}");

        List<EStimParameters> conditions = EStimSpecWriter.buildAllConditions(parsed);
        assertEquals(2, conditions.size());

        ChannelEStimParameters first = conditions.get(0).geteStimParametersForChannels().get(RHSChannel.A025);
        assertEquals(3.5, first.getWaveformParameters().getA1());
        assertEquals(3.5, first.getWaveformParameters().getA2());

        ChannelEStimParameters second = conditions.get(1).geteStimParametersForChannels().get(RHSChannel.A025);
        assertEquals(5.0, second.getWaveformParameters().getA1());
        assertEquals(5.0, second.getWaveformParameters().getA2());
    }

    public void testSplitPolarity_twoConditions() {
        Map<String, Object> parsed = parser.parse(
                "channels=[\"A025\"]. polarity={NegativeFirst;PositiveFirst}");

        List<EStimParameters> conditions = EStimSpecWriter.buildAllConditions(parsed);
        assertEquals(2, conditions.size());

        assertEquals(StimulationPolarity.NegativeFirst,
                conditions.get(0).geteStimParametersForChannels().get(RHSChannel.A025)
                        .getWaveformParameters().getPolarity());
        assertEquals(StimulationPolarity.PositiveFirst,
                conditions.get(1).geteStimParametersForChannels().get(RHSChannel.A025)
                        .getWaveformParameters().getPolarity());
    }

    public void testCartesianProduct_twoSplits() {
        Map<String, Object> parsed = parser.parse(
                "channels=[\"A025\"]. a={(3.5,3.5);(5,5)}. polarity={NegativeFirst;PositiveFirst}");

        List<EStimParameters> conditions = EStimSpecWriter.buildAllConditions(parsed);
        assertEquals(4, conditions.size());

        WaveformParameters wf0 = conditions.get(0).geteStimParametersForChannels()
                .get(RHSChannel.A025).getWaveformParameters();
        assertEquals(3.5, wf0.getA1());
        assertEquals(StimulationPolarity.NegativeFirst, wf0.getPolarity());

        WaveformParameters wf3 = conditions.get(3).geteStimParametersForChannels()
                .get(RHSChannel.A025).getWaveformParameters();
        assertEquals(5.0, wf3.getA1());
        assertEquals(StimulationPolarity.PositiveFirst, wf3.getPolarity());
    }

    public void testSplitWithNonSplitOverride() {
        Map<String, Object> parsed = parser.parse(
                "channels=[\"A025\"]. a={(3.5,3.5);(5,5)}. dp=50");

        List<EStimParameters> conditions = EStimSpecWriter.buildAllConditions(parsed);
        assertEquals(2, conditions.size());

        for (EStimParameters condition : conditions) {
            assertEquals(50.0, condition.geteStimParametersForChannels()
                    .get(RHSChannel.A025).getWaveformParameters().getDp());
        }
    }

    public void testMissingChannelsThrows() {
        Map<String, Object> parsed = parser.parse("a=(3.5,3.5)");
        try {
            EStimSpecWriter.parseChannels(parsed);
            fail("Expected IllegalArgumentException");
        } catch (IllegalArgumentException e) {
            // expected
        }
    }

    public void testComputeNumPulses_exactMatch() {
        // 200 Hz -> 5000 µs period, 200 ms -> 40 pulses
        assertEquals(40, EStimSpecWriter.computeNumPulses(null, 200.0, 5000.0, 200.0));
    }

    public void testComputeNumPulses_roundsDown() {
        // 7 ms / 5000 µs period = 1.4 -> 1
        assertEquals(1, EStimSpecWriter.computeNumPulses(null, 7.0, 5000.0, 200.0));
    }

    public void testComputeNumPulses_overrideHonored() {
        assertEquals(10, EStimSpecWriter.computeNumPulses(10, 9999.0, 5000.0, 200.0));
    }
}
