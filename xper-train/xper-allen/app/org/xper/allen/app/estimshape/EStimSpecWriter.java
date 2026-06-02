package org.xper.allen.app.estimshape;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.intan.stimulation.*;
import org.xper.allen.util.AllenDbUtil;
import org.xper.intan.stimulation.*;
import org.xper.util.FileUtil;

import java.util.*;

public class EStimSpecWriter {

    // Hard hardware limit on number of pulses per train (Intan RHS)
    public static final int MAX_PULSES_PER_TRAIN = 256;

    // Waveform defaults
    static StimulationShape defaultShape = StimulationShape.BiphasicWithInterphaseDelay;
    static StimulationPolarity defaultPolarity = StimulationPolarity.NegativeFirst;
    static double defaultD1 = 200.0;   // µs
    static double defaultD2 = 200.0;   // µs
    static double defaultDp = 100.0;   // µs
    static double defaultA1 = 2.5;     // µA
    static double defaultA2 = 2.5;     // µA

    // Pulse train defaults (new edge-triggered paradigm)
    static TriggerEdgeOrLevel defaultTriggerType = TriggerEdgeOrLevel.Edge;
    static double defaultPulseFreqHz = 200.0;
    static double defaultPulseDurationMs = 200.0;
    static double defaultPostTriggerDelayMs = 100.0;
    static double defaultRefractoryPeriodMs = 100.0;
    static GroundMode defaultGroundMode = GroundMode.PostTrain;

    /**
     * Generates EStim parameter sets and writes them to the database.
     *
     * Takes a single argument: a parameter string that specifies channels and optional
     * overrides to the default stimulation template. Unspecified parameters use defaults.
     *
     * Syntax:
     *   - Parameters separated by ". "
     *   - channels (required): list of channels, e.g. ["A025","A030"]
     *   - Use {} with ; to split into multiple conditions (cartesian product)
     *
     * Waveform parameters (per phase, microseconds / microamps):
     *   shape       StimulationShape enum (Biphasic, BiphasicWithInterphaseDelay, Triphasic, Monophasic)
     *   polarity    StimulationPolarity enum (NegativeFirst, PositiveFirst)
     *   d           tuple (d1,d2) phase durations in µs
     *   d1, d2      individual phase duration overrides in µs
     *   dp          interphase delay in µs
     *   a           tuple (a1,a2) phase amplitudes in µA
     *   a1, a2      individual phase amplitude overrides in µA
     *
     * Pulse train parameters:
     *   triggerType         Edge | Level (default Edge)
     *                       Edge: train fires once per rising edge; numPulses bounded.
     *                       Level: pulses keep firing while trigger is held high, separated by refractory.
     *   freq                pulse frequency in Hz (default 200). Determines train period = 1/freq.
     *   duration            target train duration in ms (default 200). numPulses = floor(duration / period).
     *                       Errors if numPulses would exceed 256.
     *                       Warns and rounds down if duration is not an integer multiple of the period.
     *   numPulses           OVERRIDE: explicitly set number of pulses (ignores duration). Capped at 256.
     *   triggerDelayMs      post-trigger delay in ms (default 100). Time from trigger to first pulse.
     *                       In Edge mode this is independent of refractory; in Level mode it adds latency
     *                       between successive pulses.
     *   refractoryPeriodMs  post-train refractory in ms (default 100). Time after train completes
     *                       before another trigger can be accepted (and during which charge recovery
     *                       runs if enabled).
     *
     * Legacy microsecond aliases (kept for backwards compatibility — prefer the *Ms forms above):
     *   triggerDelay        post-trigger delay in µs
     *   refractoryPeriod    post-train refractory in µs
     *
     * Ground / charge recovery:
     *   groundMode    PostTrain | BetweenPulse (default PostTrain)
     *                 PostTrain: ground-only channels mirror the stim train (zero amplitude).
     *                            Charge recovery happens AFTER the train (Intan hardware limitation).
     *                 BetweenPulse: ground-only channels use Level + SinglePulse with refractory
     *                            sized to interleave with stim pulses. Reproduces the original
     *                            "edge hold to ground" paradigm. Requires a held-high trigger
     *                            spanning the stim train duration.
     *
     * Splits — wrap any value in {a;b;c} to generate the cartesian product across all splits.
     *
     * Examples:
     *   # Single condition with defaults (Edge, 200 Hz, 200 ms, PostTrain ground)
     *   channels=["A025","A030"]
     *
     *   # Override amplitude
     *   channels=["A025","A030"]. a=(3.5,3.5)
     *
     *   # 100 ms train at 100 Hz, between-pulse grounding
     *   channels=["A025"]. freq=100. duration=100. groundMode=BetweenPulse
     *
     *   # Cartesian product across amplitude and polarity (4 conditions)
     *   channels=["A025","A030"]. a={(3.5,3.5);(5,5)}. polarity={NegativeFirst;PositiveFirst}
     */
    public static void main(String[] args) {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));
        AllenDbUtil dbUtil = context.getBean(AllenDbUtil.class);

        EStimParamParser parser = new EStimParamParser();
        Map<String, Object> parsed = parser.parse(args[0]);

        // Pull groundMode out before building conditions (it's a top-level decorator setting)
        GroundMode groundMode = defaultGroundMode;
        if (parsed.containsKey("groundMode")) {
            groundMode = GroundMode.valueOf((String) parsed.remove("groundMode"));
        }

        List<EStimParameters> allEStimParameters = buildAllConditions(parsed);

        ChargeRecoveryDecorator decorator = new ChargeRecoveryDecorator(groundMode);
        List<EStimParameters> decoratedParameters = new ArrayList<EStimParameters>();
        for (EStimParameters eStimParams : allEStimParameters) {
            decoratedParameters.add(decorator.decorate(eStimParams));
        }

        List<Long> estimIds = dbUtil.readEStimObjIds();
        Long maxId = estimIds.stream().max(new Comparator<Long>() {
            @Override
            public int compare(Long o1, Long o2) {
                return o1.compareTo(o2);
            }
        }).orElse(0L);

        Long nextId = maxId + 1;
        for (EStimParameters decorated : decoratedParameters) {
            dbUtil.writeEStimObjData(nextId, decorated.toXml(), "");
            System.out.println("Wrote EStim Obj with id: " + nextId);
            nextId += 1;
        }
    }

    static ChannelEStimParameters buildChannelParams(Map<String, Object> parsed) {
        StimulationShape shape = defaultShape;
        StimulationPolarity polarity = defaultPolarity;
        double d1 = defaultD1;
        double d2 = defaultD2;
        double dp = defaultDp;
        double a1 = defaultA1;
        double a2 = defaultA2;

        TriggerEdgeOrLevel triggerType = defaultTriggerType;
        double freqHz = defaultPulseFreqHz;
        double durationMs = defaultPulseDurationMs;
        double postTriggerDelayUs = defaultPostTriggerDelayMs * 1000.0;
        double refractoryPeriodUs = defaultRefractoryPeriodMs * 1000.0;
        Integer numPulsesOverride = null;

        if (parsed.containsKey("shape")) {
            shape = StimulationShape.valueOf((String) parsed.remove("shape"));
        }
        if (parsed.containsKey("polarity")) {
            polarity = StimulationPolarity.valueOf((String) parsed.remove("polarity"));
        }
        if (parsed.containsKey("d")) {
            ParsedTuple d = (ParsedTuple) parsed.remove("d");
            d1 = Double.parseDouble(d.get(0));
            d2 = Double.parseDouble(d.get(1));
        }
        if (parsed.containsKey("d1")) {
            d1 = Double.parseDouble((String) parsed.remove("d1"));
        }
        if (parsed.containsKey("d2")) {
            d2 = Double.parseDouble((String) parsed.remove("d2"));
        }
        if (parsed.containsKey("dp")) {
            dp = Double.parseDouble((String) parsed.remove("dp"));
        }
        if (parsed.containsKey("a")) {
            ParsedTuple a = (ParsedTuple) parsed.remove("a");
            a1 = Double.parseDouble(a.get(0));
            a2 = Double.parseDouble(a.get(1));
        }
        if (parsed.containsKey("a1")) {
            a1 = Double.parseDouble((String) parsed.remove("a1"));
        }
        if (parsed.containsKey("a2")) {
            a2 = Double.parseDouble((String) parsed.remove("a2"));
        }

        if (parsed.containsKey("triggerType")) {
            triggerType = TriggerEdgeOrLevel.valueOf((String) parsed.remove("triggerType"));
        }
        if (parsed.containsKey("freq")) {
            freqHz = Double.parseDouble((String) parsed.remove("freq"));
        }
        if (parsed.containsKey("duration")) {
            durationMs = Double.parseDouble((String) parsed.remove("duration"));
        }
        if (parsed.containsKey("numPulses")) {
            numPulsesOverride = Integer.parseInt((String) parsed.remove("numPulses"));
        }
        if (parsed.containsKey("triggerDelayMs")) {
            postTriggerDelayUs = Double.parseDouble((String) parsed.remove("triggerDelayMs")) * 1000.0;
        }
        if (parsed.containsKey("triggerDelay")) {
            postTriggerDelayUs = Double.parseDouble((String) parsed.remove("triggerDelay"));
        }
        if (parsed.containsKey("refractoryPeriodMs")) {
            refractoryPeriodUs = Double.parseDouble((String) parsed.remove("refractoryPeriodMs")) * 1000.0;
        }
        if (parsed.containsKey("refractoryPeriod")) {
            refractoryPeriodUs = Double.parseDouble((String) parsed.remove("refractoryPeriod"));
        }

        double pulseTrainPeriodUs = 1_000_000.0 / freqHz;
        int numPulses = computeNumPulses(numPulsesOverride, durationMs, pulseTrainPeriodUs, freqHz);

        // Always use PulseTrain repetition. PulseTrainParameters' constructor silently rewrites
        // numRepetitions and pulseTrainPeriod when SinglePulse is selected, which corrupts the
        // values we want for a 1-pulse train. PulseTrain with numPulses=1 fires identically on Intan.
        WaveformParameters waveform = new WaveformParameters(shape, polarity, d1, d2, dp, a1, a2);

        PulseTrainParameters pulseTrainParameters = new PulseTrainParameters(
                PulseRepetition.PulseTrain,
                numPulses,
                pulseTrainPeriodUs,
                refractoryPeriodUs,
                triggerType,
                postTriggerDelayUs
        );

        ChargeRecoveryParameters chargeRecoveryParameters = new ChargeRecoveryParameters(
                true,
                0.0,
                refractoryPeriodUs
        );

        return new ChannelEStimParameters(
                waveform,
                pulseTrainParameters,
                new AmpSettleParameters(),
                chargeRecoveryParameters
        );
    }

    /**
     * Resolve numPulses from either an explicit override or from duration + freq.
     * Throws IllegalArgumentException if the result exceeds MAX_PULSES_PER_TRAIN.
     * Prints a warning to stderr if duration is not an integer multiple of the period
     * (the actual achieved duration is rounded down).
     */
    static int computeNumPulses(Integer numPulsesOverride, double durationMs, double pulseTrainPeriodUs, double freqHz) {
        if (numPulsesOverride != null) {
            if (numPulsesOverride > MAX_PULSES_PER_TRAIN) {
                throw new IllegalArgumentException(String.format(
                        "numPulses=%d exceeds Intan RHS max of %d pulses per train.",
                        numPulsesOverride, MAX_PULSES_PER_TRAIN));
            }
            if (numPulsesOverride < 1) {
                throw new IllegalArgumentException("numPulses must be >= 1, got " + numPulsesOverride);
            }
            return numPulsesOverride;
        }

        double durationUs = durationMs * 1000.0;
        double exact = durationUs / pulseTrainPeriodUs;
        int numPulses = (int) Math.floor(exact);
        if (numPulses < 1) {
            throw new IllegalArgumentException(String.format(
                    "duration=%.3f ms is shorter than one pulse period (%.3f µs at %.1f Hz).",
                    durationMs, pulseTrainPeriodUs, freqHz));
        }
        if (numPulses > MAX_PULSES_PER_TRAIN) {
            double maxDurationMs = MAX_PULSES_PER_TRAIN * pulseTrainPeriodUs / 1000.0;
            throw new IllegalArgumentException(String.format(
                    "duration=%.3f ms at %.1f Hz requires %d pulses, exceeds Intan RHS max of %d. " +
                            "Max duration at this frequency is %.3f ms (or lower the frequency).",
                    durationMs, freqHz, numPulses, MAX_PULSES_PER_TRAIN, maxDurationMs));
        }

        double actualDurationMs = numPulses * pulseTrainPeriodUs / 1000.0;
        if (Math.abs(actualDurationMs - durationMs) > 1e-6) {
            System.err.println(String.format(
                    "WARNING: requested duration=%.3f ms is not an integer multiple of the pulse period " +
                            "(%.3f µs at %.1f Hz). Rounding down to %d pulses = %.3f ms actual duration.",
                    durationMs, pulseTrainPeriodUs, freqHz, numPulses, actualDurationMs));
        }
        return numPulses;
    }

    static List<EStimParameters> buildAllConditions(Map<String, Object> parsed) {
        Map<String, Object> working = new LinkedHashMap<String, Object>(parsed);

        List<String> splitKeys = new ArrayList<String>();
        for (Map.Entry<String, Object> entry : working.entrySet()) {
            if (entry.getValue() instanceof ParsedSplit) {
                splitKeys.add(entry.getKey());
            }
        }

        if (splitKeys.isEmpty()) {
            List<RHSChannel> channels = parseChannels(working);
            ChannelEStimParameters channelParams = buildChannelParams(working);
            validateNoRemainingKeys(working);

            EStimParameters eStim = new EStimParameters();
            for (RHSChannel channel : channels) {
                eStim.put(channel, channelParams);
            }
            List<EStimParameters> result = new ArrayList<EStimParameters>();
            result.add(eStim);
            return result;
        }

        List<int[]> combinations = cartesianProduct(splitKeys, working);

        for (String key : splitKeys) {
            working.remove(key);
        }

        List<EStimParameters> result = new ArrayList<EStimParameters>();
        for (int i = 0; i < combinations.size(); i++) {
            int[] combo = combinations.get(i);
            Map<String, Object> resolved = new LinkedHashMap<String, Object>(working);
            for (int j = 0; j < splitKeys.size(); j++) {
                String key = splitKeys.get(j);
                ParsedSplit split = (ParsedSplit) parsed.get(key);
                resolved.put(key, split.get(combo[j]));
            }

            List<RHSChannel> channels = parseChannels(resolved);
            ChannelEStimParameters channelParams = buildChannelParams(resolved);

            if (i == 0) {
                validateNoRemainingKeys(resolved);
            }

            EStimParameters eStim = new EStimParameters();
            for (RHSChannel channel : channels) {
                eStim.put(channel, channelParams);
            }
            result.add(eStim);
        }

        return result;
    }

    private static void validateNoRemainingKeys(Map<String, Object> remaining) {
        if (!remaining.isEmpty()) {
            throw new IllegalArgumentException(
                    "Unrecognized parameter(s): " + remaining.keySet()
                            + ". Valid parameters: channels, shape, polarity, d, d1, d2, dp, a, a1, a2, "
                            + "triggerType, freq, duration, numPulses, "
                            + "triggerDelayMs, triggerDelay, refractoryPeriodMs, refractoryPeriod, "
                            + "groundMode");
        }
    }

    private static List<int[]> cartesianProduct(List<String> splitKeys, Map<String, Object> parsed) {
        List<int[]> result = new ArrayList<int[]>();
        int[] sizes = new int[splitKeys.size()];
        for (int i = 0; i < splitKeys.size(); i++) {
            sizes[i] = ((ParsedSplit) parsed.get(splitKeys.get(i))).size();
        }

        int[] current = new int[splitKeys.size()];
        cartesianHelper(result, current, sizes, 0);
        return result;
    }

    private static void cartesianHelper(List<int[]> result, int[] current, int[] sizes, int depth) {
        if (depth == sizes.length) {
            result.add(Arrays.copyOf(current, current.length));
            return;
        }
        for (int i = 0; i < sizes[depth]; i++) {
            current[depth] = i;
            cartesianHelper(result, current, sizes, depth + 1);
        }
    }

    static List<RHSChannel> parseChannels(Map<String, Object> parsed) {
        Object channelsVal = parsed.remove("channels");
        if (channelsVal == null) {
            throw new IllegalArgumentException("channels is required");
        }
        if (!(channelsVal instanceof ParsedList)) {
            throw new IllegalArgumentException("channels must be a list, e.g. [\"A025\",\"A030\"]");
        }

        ParsedList list = (ParsedList) channelsVal;
        List<RHSChannel> channels = new ArrayList<RHSChannel>();
        for (int i = 0; i < list.size(); i++) {
            channels.add(RHSChannel.valueOf(list.get(i)));
        }
        return channels;
    }
}
