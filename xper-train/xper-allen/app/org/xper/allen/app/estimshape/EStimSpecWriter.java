package org.xper.allen.app.estimshape;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.intan.stimulation.*;
import org.xper.allen.util.AllenDbUtil;
import org.xper.intan.stimulation.*;
import org.xper.util.FileUtil;

import java.util.*;

public class EStimSpecWriter {

    // Template defaults
    static StimulationShape defaultShape = StimulationShape.BiphasicWithInterphaseDelay;
    static StimulationPolarity defaultPolarity = StimulationPolarity.PositiveFirst;
    static double defaultD1 = 200.0;
    static double defaultD2 = 200.0;
    static double defaultDp = 100.0;
    static double defaultA1 = 2.5;
    static double defaultA2 = 2.5;
    static int defaultPostStimRefractoryPeriod = 2000;
    static PulseRepetition defaultPulseRepetition = PulseRepetition.SinglePulse;
    static int defaultNumRepetitions = 1;
    static double defaultPulseTrainPeriod = 10.0;
    static TriggerEdgeOrLevel defaultTriggerEdgeOrLevel = TriggerEdgeOrLevel.Level;
    static double defaultPostTriggerDelay = 0.0;

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

    /**
     * Builds all conditions by computing the cartesian product of any split parameters.
     * Non-split parameters are constant across all conditions.
     */
    static List<EStimParameters> buildAllConditions(Map<String, Object> parsed) {
        // Find which keys have splits
        List<String> splitKeys = new ArrayList<String>();
        for (Map.Entry<String, Object> entry : parsed.entrySet()) {
            if (entry.getValue() instanceof ParsedSplit) {
                splitKeys.add(entry.getKey());
            }
        }

        // If no splits, just one condition
        if (splitKeys.isEmpty()) {
            List<RHSChannel> channels = parseChannels(parsed);
            ChannelEStimParameters channelParams = buildChannelParams(parsed);
            EStimParameters eStim = new EStimParameters();
            for (RHSChannel channel : channels) {
                eStim.put(channel, channelParams);
            }
            List<EStimParameters> result = new ArrayList<EStimParameters>();
            result.add(eStim);
            return result;
        }

        // Build cartesian product of split indices
        List<int[]> combinations = cartesianProduct(splitKeys, parsed);

        List<EStimParameters> result = new ArrayList<EStimParameters>();
        for (int[] combo : combinations) {
            // Build a resolved map for this combination
            Map<String, Object> resolved = new LinkedHashMap<String, Object>(parsed);
            for (int i = 0; i < splitKeys.size(); i++) {
                String key = splitKeys.get(i);
                ParsedSplit split = (ParsedSplit) parsed.get(key);
                resolved.put(key, split.get(combo[i]));
            }

            List<RHSChannel> channels = parseChannels(resolved);
            ChannelEStimParameters channelParams = buildChannelParams(resolved);
            EStimParameters eStim = new EStimParameters();
            for (RHSChannel channel : channels) {
                eStim.put(channel, channelParams);
            }
            result.add(eStim);
        }

        return result;
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
        Object channelsVal = parsed.get("channels");
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
            shape = StimulationShape.valueOf((String) parsed.get("shape"));
        }
        if (parsed.containsKey("pol")) {
            polarity = StimulationPolarity.valueOf((String) parsed.get("pol"));
        }
        if (parsed.containsKey("d")) {
            ParsedTuple d = (ParsedTuple) parsed.get("d");
            d1 = Double.parseDouble(d.get(0));
            d2 = Double.parseDouble(d.get(1));
        }
        if (parsed.containsKey("d1")) {
            d1 = Double.parseDouble((String) parsed.get("d1"));
        }
        if (parsed.containsKey("d2")) {
            d2 = Double.parseDouble((String) parsed.get("d2"));
        }
        if (parsed.containsKey("dp")) {
            dp = Double.parseDouble((String) parsed.get("dp"));
        }
        if (parsed.containsKey("a")) {
            ParsedTuple a = (ParsedTuple) parsed.get("a");
            a1 = Double.parseDouble(a.get(0));
            a2 = Double.parseDouble(a.get(1));
        }
        if (parsed.containsKey("a1")) {
            a1 = Double.parseDouble((String) parsed.get("a1"));
        }
        if (parsed.containsKey("a2")) {
            a2 = Double.parseDouble((String) parsed.get("a2"));
        }
        if (parsed.containsKey("refrac")) {
            postStimRefractoryPeriod = Integer.parseInt((String) parsed.get("refrac"));
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
}