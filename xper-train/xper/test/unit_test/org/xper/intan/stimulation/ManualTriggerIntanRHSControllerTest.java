package org.xper.intan.stimulation;

import org.junit.Before;
import org.junit.Ignore;
import org.junit.Test;
import org.xper.XperConfig;
import org.xper.intan.IntanClient;
import org.xper.time.DefaultTimeUtil;
import org.xper.util.ResourceUtil;
import org.xper.util.ThreadUtil;

import java.util.*;

import static org.junit.Assert.*;

public class ManualTriggerIntanRHSControllerTest {

    private IntanClient intanClient;
    private ManualTriggerIntanRHS controller;

    @Before
    public void setUp() throws Exception {
        List<String> libs = new ArrayList<String>();
        libs.add("xper");
        new XperConfig("", libs);

        intanClient = new IntanClient();
        intanClient.setTimeUtil(new DefaultTimeUtil());
        intanClient.setHost("172.30.9.78");
        intanClient.setPort(5000);


        controller = new ManualTriggerIntanRHS();
        controller.setIntanClient(intanClient);
        controller.setDefaultParameters(defaultParameters());

        controller.connect();
//        assertTrue(controller.getIntanClient().get("b-000.maintainampsettle").equals("True"));
    }

    @Test
    public void testImpedanceTest(){
        controller.setDefaultSavePath("/home/i2_allen/Documents/Test/Impedance");
        controller.setDefaultBaseFileName("TestImpedanceMeasurement");
        controller.testImpedance();
    }
    /**
     * Times the current full setupManualStimulationFor as a baseline.
     */
    @Test
    public void timeOriginalSetup() {
        EStimParameters eStimParameters = makeTestEStimParams();

        long start = System.currentTimeMillis();
        controller.setupManualStimulationFor(eStimParameters);
        long elapsed = System.currentTimeMillis() - start;

        System.out.println("=== Original setupManualStimulationFor: " + elapsed + " ms ===");
    }

    /**
     * Times a batched approach that skips per-command verification.
     *
     * WHY the original is slow (now that we can see IntanClient.set()):
     *   set() sends the command, then enters a polling loop calling get()
     *   repeatedly until the value is confirmed. That means each of the ~20
     *   parameters per channel costs 1 write + N reads. For 2 channels that's
     *   ~40 verified sets = potentially hundreds of TCP round-trips.
     *
     * This test sends ALL commands in one TCP write with semicolon separation,
     * drains server responses, then spot-checks a couple values at the end.
     */
    @Test
    public void timeBatchedSetup() {
        EStimParameters eStimParameters = makeTestEStimParams();
        Map<RHSChannel, ChannelEStimParameters> parametersForChannels =
                eStimParameters.geteStimParametersForChannels();

        long start = System.currentTimeMillis();

        // -- Phase 1: Batched disableAllStim --
        long disableStart = System.currentTimeMillis();
        disableAllStimBatched();
        long disableTime = System.currentTimeMillis() - disableStart;

        // -- Phase 2: Batched parameter setting --
        long paramStart = System.currentTimeMillis();

        List<String> allCmds = new ArrayList<>();
        for (RHSChannel channel : parametersForChannels.keySet()) {
            String tcpName = ManualTriggerIntanRHS.tcpNameForIntanChannel(channel);
            ChannelEStimParameters chParams = parametersForChannels.get(channel);
            addAllChannelCommands(tcpName, chParams, allCmds);
        }
        intanClient.sendBatch(allCmds);

        long paramTime = System.currentTimeMillis() - paramStart;

        // -- Phase 3: Upload (unavoidable, same as original) --
        long uploadStart = System.currentTimeMillis();
        controller.uploadParameters(parametersForChannels.keySet());
        long uploadTime = System.currentTimeMillis() - uploadStart;

        long totalElapsed = System.currentTimeMillis() - start;

        System.out.println("=== Batched Setup Breakdown ===");
        System.out.println("  disableAllStim:    " + disableTime + " ms");
        System.out.println("  parameter setting: " + paramTime + " ms");
        System.out.println("  upload:            " + uploadTime + " ms");
        System.out.println("  TOTAL:             " + totalElapsed + " ms");

        // Spot-check that it actually worked
        String stimEnabled = intanClient.get("a-025.stimenabled");
        String polarity = intanClient.get("a-025.polarity");
        assertTrue("stimenabled should be True, got: " + stimEnabled,
                stimEnabled.equalsIgnoreCase("True"));
        assertTrue("polarity should be NegativeFirst, got: " + polarity,
                polarity.equalsIgnoreCase("NegativeFirst"));

        System.out.println("  Verification passed.");
    }

    /**
     * Isolates just the disableAllStim comparison.
     * Does NOT require sendBatch() - uses existing set() calls only.
     * Tests the fix for querying channel count once per port instead of per channel.
     */
    @Test
    public void timeDisableAllStimComparison() {
        // Time original
        long start = System.currentTimeMillis();
        controller.disableAllStim();
        long originalTime = System.currentTimeMillis() - start;

        // Time fixed (query once per port, still individual set() calls)
        start = System.currentTimeMillis();
        disableAllStimFixed();
        long fixedTime = System.currentTimeMillis() - start;

        // Time batched (query once per port, single TCP write for all disables)
        start = System.currentTimeMillis();
        disableAllStimBatched();
        long batchedTime = System.currentTimeMillis() - start;

        System.out.println("=== disableAllStim comparison ===");
        System.out.println("  Original:          " + originalTime + " ms");
        System.out.println("  Fixed (no batch):  " + fixedTime + " ms");
        System.out.println("  Batched:           " + batchedTime + " ms");
        if (batchedTime > 0) {
            System.out.println("  Speedup (orig vs batched): " + String.format("%.1fx", (double) originalTime / batchedTime));
        }
    }

    // ──────────────────────────────────────────────
    // Helper methods
    // ──────────────────────────────────────────────

    private void disableAllStimFixed() {
        for (String port : Arrays.asList("a", "b", "c", "d")) {
            int numChannels = getPortChannelCountSafe(port);
            if (numChannels > 0) {
                for (int ch = 0; ch <= 31; ch++) {
                    intanClient.set(String.format("%s-%03d.stimenabled", port, ch), "false");
                }
            }
        }
    }

    private void disableAllStimBatched() {
        List<String> cmds = new ArrayList<>();
        for (String port : Arrays.asList("a", "b", "c", "d")) {
            int numChannels = getPortChannelCountSafe(port);
            if (numChannels > 0) {
                for (int ch = 0; ch <= 31; ch++) {
                    cmds.add(String.format("set %s-%03d.stimenabled false", port, ch));
                }
            }
        }
        if (!cmds.isEmpty()) {
            intanClient.sendBatch(cmds);
        }
    }

    private int getPortChannelCountSafe(String port) {
        while (true) {
            ThreadUtil.sleep(100);
            String out = intanClient.get(port + ".numberamplifierchannels");
            try {
                return Integer.parseInt(out);
            } catch (NumberFormatException e) {
                // retry
            }
        }
    }

    private void addAllChannelCommands(String tcpName, ChannelEStimParameters chParams, List<String> cmds) {
        cmds.add("set " + tcpName + ".stimenabled true");
        cmds.add("set " + tcpName + ".source keypressf1");

        for (Parameter parameter : controller.getDefaultParameters()) {
            cmds.add("set " + tcpName + "." + parameter.getKey().toLowerCase()
                    + " " + parameter.getValue().toString().toLowerCase());
        }

        PulseTrainParameters p = chParams.getPulseTrainParameters();
        cmds.add("set " + tcpName + ".triggeredgeorlevel " + p.triggerEdgeOrLevel);
        cmds.add("set " + tcpName + ".pulseortrain " + p.pulseRepetition);
        cmds.add("set " + tcpName + ".numberofstimpulses " + p.numRepetitions);
        cmds.add("set " + tcpName + ".pulsetrainperiodmicroseconds " + p.pulseTrainPeriod);
        cmds.add("set " + tcpName + ".refractoryperiodmicroseconds " + p.postStimRefractoryPeriod);
        cmds.add("set " + tcpName + ".posttriggerdelaymicroseconds " + p.postTriggerDelay);

        WaveformParameters w = chParams.getWaveformParameters();
        cmds.add("set " + tcpName + ".shape " + w.shape);
        cmds.add("set " + tcpName + ".polarity " + w.polarity);
        cmds.add("set " + tcpName + ".firstphasedurationmicroseconds " + w.d1);
        cmds.add("set " + tcpName + ".secondphasedurationmicroseconds " + w.d2);
        cmds.add("set " + tcpName + ".interphasedelaymicroseconds " + w.dp);
        cmds.add("set " + tcpName + ".firstphaseamplitudemicroamps " + w.a1);
        cmds.add("set " + tcpName + ".secondphaseamplitudemicroamps " + w.a2);

        AmpSettleParameters a = chParams.getAmpSettleParameters();
        if (a != null) {
            cmds.add("set " + tcpName + ".enableampsettle " + a.enableAmpSettle);
            cmds.add("set " + tcpName + ".prestimampsettlemicroseconds " + a.preStimAmpSettle);
            cmds.add("set " + tcpName + ".poststimampsettlemicroseconds " + a.postStimAmpSettle);
            cmds.add("set " + tcpName + ".maintainampsettle " + a.maintainAmpSettleDuringPulseTrain);
        }

        ChargeRecoveryParameters cr = chParams.getChargeRecoveryParameters();
        if (cr != null) {
            cmds.add("set " + tcpName + ".enablechargerecovery " + cr.enableChargeRecovery);
            cmds.add("set " + tcpName + ".poststimchargerecovonmicroseconds " + cr.postStimChargeRecoveryOn);
            cmds.add("set " + tcpName + ".poststimchargerecovoffmicroseconds " + cr.postStimChargeRecoveryOff);
        }
    }

    private EStimParameters makeTestEStimParams() {
        Map<RHSChannel, ChannelEStimParameters> parametersForChannels = new LinkedHashMap<>();

        WaveformParameters waveformParameters = new WaveformParameters(
                StimulationShape.Biphasic,
                StimulationPolarity.NegativeFirst,
                200.0, 200.0, 0.0, 2.5, 2.5
        );

        PulseTrainParameters pulseTrainParameters = new PulseTrainParameters(
                PulseRepetition.SinglePulse,
                1, 0.0, 0.0,
                TriggerEdgeOrLevel.Edge, 0.0
        );

        ChannelEStimParameters channelEStimParameters = new ChannelEStimParameters(
                waveformParameters, pulseTrainParameters);
        parametersForChannels.put(RHSChannel.A025, channelEStimParameters);
        parametersForChannels.put(RHSChannel.A022, channelEStimParameters);

        return new EStimParameters(parametersForChannels);
    }

    @Ignore
    @Test
    public void enumToStringTest(){
        PulseRepetition pulseRepetition = PulseRepetition.PulseTrain;
        String pulseRepetitionString = pulseRepetition.toString();
        assertEquals("PulseTrain", pulseRepetitionString);
    }

    @Test
    public void tcpNameForIntanChannel() {
        String channelString = ManualTriggerIntanRHS.tcpNameForIntanChannel(RHSChannel.A000);
        assertEquals("a-000", channelString);
    }

    @Test
    public void testStimulationSetup(){
        Map<RHSChannel, ChannelEStimParameters> parametersForChannels = new LinkedHashMap<>();
        WaveformParameters waveformParameters = new WaveformParameters(
                StimulationShape.Biphasic,
                StimulationPolarity.NegativeFirst,
                200.0,
                200.0,
                0.0,
                2.5,
                2.5
        );

        PulseTrainParameters pulseTrainParameters = new PulseTrainParameters(
                PulseRepetition.SinglePulse,
                1,
                0.0,
                0.0,
                TriggerEdgeOrLevel.Edge,
                0.0);

        ChannelEStimParameters channelEStimParameters = new ChannelEStimParameters(waveformParameters, pulseTrainParameters);
        parametersForChannels.put(RHSChannel.A025, channelEStimParameters);
        parametersForChannels.put(RHSChannel.A022, channelEStimParameters);
        EStimParameters eStimParameters = new EStimParameters(parametersForChannels);

        controller.setupManualStimulationFor(eStimParameters);

        String stim_enabled = controller.getIntanClient().get("a-025.stimenabled");
        assertTrue(stim_enabled.equals("True"));

        assertTrue(controller.getIntanClient().get("a-025.polarity").equals("NegativeFirst"));
    }

    @Test
    public void testPulse(){
        Map<RHSChannel, ChannelEStimParameters> parametersForChannels = new LinkedHashMap<>();
        WaveformParameters waveformParameters = new WaveformParameters(
                StimulationShape.Biphasic,
                StimulationPolarity.PositiveFirst,
                200.0,
                200.0,
                0.0,
                2.5,
                2.5
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
        parametersForChannels.put(RHSChannel.A025, channelEStimParameters);
        parametersForChannels.put(RHSChannel.A022, channelEStimParameters);
        EStimParameters eStimParameters = new EStimParameters(parametersForChannels);

//        System.out.println(eStimParameters.toXml());

        controller.setupDigitalStimulationFor(eStimParameters);
        controller.stopRecording();


        for(int i = 0; i < 30; i++) {
            controller.trigger();
            ThreadUtil.sleep(1000);
        }
    }

    private List<Parameter<Object>> defaultParameters(){
        List<Parameter<Object>> parameters = new LinkedList<>();
//        parameters.add(new Parameter<>("MaintainAmpSettle", "True"));


        return parameters;
  }
}