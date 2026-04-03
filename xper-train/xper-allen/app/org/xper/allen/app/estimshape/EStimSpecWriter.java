package org.xper.allen.app.estimshape;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.intan.stimulation.*;
import org.xper.allen.util.AllenDbUtil;
import org.xper.intan.stimulation.*;
import org.xper.util.FileUtil;

import java.util.*;

public class EStimSpecWriter {

    // Template defaults
    static StimulationShape defaultShape = StimulationShape.Biphasic;
    static StimulationPolarity defaultPolarity = StimulationPolarity.PositiveFirst;
    static double defaultD1 = 200.0;
    static double defaultD2 = 200.0;
    static double defaultDp = 100.0;
    static double defaultA1 = 2.5;
    static double defaultA2 = 2.5;
    static int defaultPostStimRefractoryPeriod = 3500;
    static PulseRepetition defaultPulseRepetition = PulseRepetition.SinglePulse;
    static int defaultNumRepetitions = 1;
    static double defaultPulseTrainPeriod = 10.0;
    static TriggerEdgeOrLevel defaultTriggerEdgeOrLevel = TriggerEdgeOrLevel.Level;
    static double defaultPostTriggerDelay = 50.0;

    /**
     * Generates EStim parameter sets and writes them to the database.
     *
     * Takes a single argument: a parameter string that specifies channels and optional overrides
     * to the default stimulation template. Unspecified parameters use template defaults.
     *
     * Syntax:
     *   - Parameters separated by ". "
     *   - channels (required): list of channels, e.g. ["A025","A030"]
     *   - Optional overrides: a, a1, a2, d, d1, d2, dp, pol, shape, refractoryPeriod, triggerDelay
     *   - Use {} with ; to split into multiple conditions (cartesian product)
     *
     * Examples:
     *   # Single condition with defaults
     *   channels=["A025","A030"]
     *
     *   # Override amplitude
     *   channels=["A025","A030"]. a=(3.5,3.5)
     *
     *   # Split across amplitudes (generates 2 conditions)
     *   channels=["A025","A030"]. a={(3.5,3.5);(5,5)}
     *
     *   # Cartesian product of amplitude and polarity (generates 4 conditions)
     *   channels=["A025","A030"]. a={(3.5,3.5);(5,5)}. pol={NegativeFirst;PositiveFirst}
     *
     * All generated conditions are decorated with charge recovery ground pulses
     * on remaining port A channels before being written to the database.
     */
    public static void main(String[] args) {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));
        AllenDbUtil dbUtil = context.getBean(AllenDbUtil.class);

        EStimParamParser parser = new EStimParamParser();
        Map<String, Object> parsed = parser.parse(args[0]);

        List<EStimParameters> allEStimParameters = buildAllConditions(parsed);

        // Decorate
        ChargeRecoveryDecorator decorator = new ChargeRecoveryDecorator();
        List<EStimParameters> decoratedParameters = new ArrayList<EStimParameters>();
        for (EStimParameters eStimParams : allEStimParameters) {
            decoratedParameters.add(decorator.decorate(eStimParams));
        }

        // Write to DB
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
        int postStimRefractoryPeriod = defaultPostStimRefractoryPeriod;

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
        if (parsed.containsKey("refractoryPeriod")) {
            postStimRefractoryPeriod = Integer.parseInt((String) parsed.remove("refractoryPeriod"));
        }
        if (parsed.containsKey("triggerDelay")){
            defaultPostTriggerDelay = Double.parseDouble((String) parsed.remove("triggerDelay"));
        }

        WaveformParameters waveform = new WaveformParameters(shape, polarity, d1, d2, dp, a1, a2);

        PulseTrainParameters pulseTrainParameters = new PulseTrainParameters(
                defaultPulseRepetition,
                defaultNumRepetitions,
                defaultPulseTrainPeriod,
                postStimRefractoryPeriod,
                defaultTriggerEdgeOrLevel,
                defaultPostTriggerDelay
        );

        ChargeRecoveryParameters chargeRecoveryParameters = new ChargeRecoveryParameters(
                true,
                0.0,
                (double) postStimRefractoryPeriod
        );

        return new ChannelEStimParameters(
                waveform,
                pulseTrainParameters,
                new AmpSettleParameters(),
                chargeRecoveryParameters
        );
    }

    static List<EStimParameters> buildAllConditions(Map<String, Object> parsed) {
        // Work on a mutable copy so we can consume keys
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

        // For splits, resolve and validate on first combination,
        // then proceed with the rest
        List<int[]> combinations = cartesianProduct(splitKeys, working);

        // Remove split keys from working — they'll be resolved per combination
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

            // Validate on first combination only
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
                            + ". Valid parameters: channels, a, a1, a2, d, d1, d2, dp, polarity, shape, refractoryPeriod");
        }
    }

    /**
     * Generates all index combinations for the cartesian product of splits.
     * For example, if split A has 2 values and split B has 3 values,
     * returns: [0,0], [0,1], [0,2], [1,0], [1,1], [1,2]
     */
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