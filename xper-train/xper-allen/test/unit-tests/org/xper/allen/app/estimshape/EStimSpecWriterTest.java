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
    }

    public void testOverrideAmplitudeTuple() {
        Map<String, Object> parsed = parser.parse("channels=[\"A025\"]. a=(3.5,3.5)");

        ChannelEStimParameters params = EStimSpecWriter.buildChannelParams(parsed);
        assertEquals(3.5, params.getWaveformParameters().getA1());
        assertEquals(3.5, params.getWaveformParameters().getA2());
        assertEquals(200.0, params.getWaveformParameters().getD1());
    }

    public void testOverridePolarity() {
        Map<String, Object> parsed = parser.parse("channels=[\"A025\"]. pol=PositiveFirst");

        ChannelEStimParameters params = EStimSpecWriter.buildChannelParams(parsed);
        assertEquals(StimulationPolarity.PositiveFirst, params.getWaveformParameters().getPolarity());
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
        System.out.println(conditions);
        assertEquals(2, conditions.size());

        // First condition: a=3.5
        ChannelEStimParameters first = conditions.get(0).geteStimParametersForChannels().get(RHSChannel.A025);
        assertEquals(3.5, first.getWaveformParameters().getA1());
        assertEquals(3.5, first.getWaveformParameters().getA2());

        // Second condition: a=5
        ChannelEStimParameters second = conditions.get(1).geteStimParametersForChannels().get(RHSChannel.A025);
        assertEquals(5.0, second.getWaveformParameters().getA1());
        assertEquals(5.0, second.getWaveformParameters().getA2());
    }

    public void testSplitPolarity_twoConditions() {
        Map<String, Object> parsed = parser.parse(
                "channels=[\"A025\"]. pol={NegativeFirst;PositiveFirst}");

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
                "channels=[\"A025\"]. a={(3.5,3.5);(5,5)}. pol={NegativeFirst;PositiveFirst}");

        List<EStimParameters> conditions = EStimSpecWriter.buildAllConditions(parsed);
        assertEquals(4, conditions.size());

        // (3.5, NegativeFirst)
        WaveformParameters wf0 = conditions.get(0).geteStimParametersForChannels()
                .get(RHSChannel.A025).getWaveformParameters();
        assertEquals(3.5, wf0.getA1());
        assertEquals(StimulationPolarity.NegativeFirst, wf0.getPolarity());

        // (3.5, PositiveFirst)
        WaveformParameters wf1 = conditions.get(1).geteStimParametersForChannels()
                .get(RHSChannel.A025).getWaveformParameters();
        assertEquals(3.5, wf1.getA1());
        assertEquals(StimulationPolarity.PositiveFirst, wf1.getPolarity());

        // (5, NegativeFirst)
        WaveformParameters wf2 = conditions.get(2).geteStimParametersForChannels()
                .get(RHSChannel.A025).getWaveformParameters();
        assertEquals(5.0, wf2.getA1());
        assertEquals(StimulationPolarity.NegativeFirst, wf2.getPolarity());

        // (5, PositiveFirst)
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

        // dp=50 should be constant across both conditions
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
}