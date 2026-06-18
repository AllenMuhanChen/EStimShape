package org.xper.allen.isoluminant;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.AbstractTrialGenerator;
import org.xper.rfplot.RFInfo;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.gabor.IsoGaborSpec;
import org.xper.util.FileUtil;

import java.util.*;

public class IsoGaborTrialGenerator extends AbstractTrialGenerator<Stim> {
    private static boolean isTestMixed;
    private static boolean isTestOrientations;
    private final int numRepeats = 5;
    private GaborSpec gaborSpec;
    public static final List<Double> frequencies = Arrays.asList(0.5, 1.0, 2.0, 4.0);
        public static final List<Double> orientationOffsets = Arrays.asList(0.0, 45.0, 90.0, 135.0);
//    public static final List<Double> mixedPhases = Arrays.asList(0.0, 0.5);

    // Target cycles-per-RF range and how many test frequencies should fall within it.
    private static final double MIN_CYCLES_PER_RF = 2.5;
    private static final double MAX_CYCLES_PER_RF = 8.0;
    // Minimum spacing (in cycles-per-RF) between added values and existing in-range values.
    private static final double CYCLES_PER_RF_MARGIN = 1.0;
    // Desired number of test frequencies within the cycles-per-RF range (overridable via args[2]).
    private static final int targetNumInCyclesRange = 2;
    private final Random random = new Random();

    public static void main(String[] args) {
        // Check if the argument is provided
        try {
            isTestMixed = Boolean.parseBoolean(args[0]);
        } catch (ArrayIndexOutOfBoundsException e) {
            isTestMixed = false;
        }

        try{
            isTestOrientations = Boolean.parseBoolean(args[1]);
        } catch (ArrayIndexOutOfBoundsException e) {
            isTestOrientations = false;
        }


        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"),
                IsoGaborConfig.class
        );

        IsoGaborTrialGenerator gen = context.getBean(IsoGaborTrialGenerator.class);
        gen.generate();
    }


    @Override
    protected void addTrials() {
        // Get database values
        JdbcTemplate jdbcTemplate = new JdbcTemplate(dbUtil.getDataSource());

        // Get RF Info
        RFInfo rfInfo = getRFInfo(jdbcTemplate);

        // Calculate RF based frequencies to test
        double rfDiameter = rfInfo.getRadius() * 2.0;

        // Start from the base frequencies and make sure enough of them land in the target
        // cycles-per-RF range, adding RF-scaled frequencies if needed. Work on a local copy so
        // the shared static frequencies list is never mutated.
        List<Double> frequenciesToTest = new ArrayList<>(frequencies);
        addFrequenciesForCyclesPerRF(frequenciesToTest, rfDiameter);

        // Get StimSpec
        GaborSpec stimSpec = getStimSpec(jdbcTemplate);
        double plottedOrientation = stimSpec.getOrientation();

        // Set up GaborSpec with database values
        gaborSpec = new GaborSpec();
        gaborSpec.setXCenter(rfInfo.getCenter().getX());
        gaborSpec.setYCenter(rfInfo.getCenter().getY());
        gaborSpec.setSize(rfDiameter * 1.33);
        gaborSpec.setPhase(0);
        gaborSpec.setAnimation(false);

        // Pure Gabors
        for (Double frequency : frequenciesToTest) {
            gaborSpec.setFrequency(frequency);
            if (isTestOrientations) {
                for (Double orientationOffset : orientationOffsets) {
                    gaborSpec.setOrientation(orientationOffset + plottedOrientation);
                    addIsochromaticTrials();
                    addIsoluminantTrials();
                }
            }
            else{
                gaborSpec.setOrientation(plottedOrientation);
                addIsochromaticTrials();
                addIsoluminantTrials();

            }

        }
        if (isTestMixed) {
            gaborSpec.setOrientation(plottedOrientation);
            addMixedGaborTrials();
        }
    }

    /**
     * Ensure at least {@link #targetNumInCyclesRange} of the test frequencies land within the
     * target cycles-per-RF range [{@link #MIN_CYCLES_PER_RF}, {@link #MAX_CYCLES_PER_RF}].
     *
     * Frequencies already in range are kept. Any shortfall is filled with randomly chosen
     * cycles-per-RF values that keep a {@link #CYCLES_PER_RF_MARGIN} margin from the existing
     * in-range values and from each other (so e.g. a single existing in-range frequency gets a
     * spaced-out partner, and an empty range gets up to the target number of values spread
     * roughly uniformly across it). Each chosen cycles-per-RF value is converted to a frequency
     * (frequency = cyclesPerRF / rfDiameter) and appended to {@code frequenciesToTest}.
     *
     * @param frequenciesToTest list of frequencies to append to (modified in place)
     * @param rfDiameter        receptive field diameter (same spatial units as the frequencies)
     */
    private void addFrequenciesForCyclesPerRF(List<Double> frequenciesToTest, double rfDiameter) {
        // Collect cycles-per-RF values that already fall in the target range.
        List<Double> chosenCycles = new ArrayList<>();
        for (Double frequency : frequenciesToTest) {
            double cyclesPerRF = frequency * rfDiameter;
            if (cyclesPerRF >= MIN_CYCLES_PER_RF && cyclesPerRF <= MAX_CYCLES_PER_RF) {
                chosenCycles.add(cyclesPerRF);
            }
        }

        int numToAdd = targetNumInCyclesRange - chosenCycles.size();
        if (numToAdd <= 0) {
            return;
        }

        // Sample additional cycles-per-RF values, keeping a margin from values already chosen.
        for (int i = 0; i < numToAdd; i++) {
            Double newCyclesPerRF = sampleCyclesPerRFWithMargin(chosenCycles);
            if (newCyclesPerRF == null) {
                // Could not satisfy the margin; stop rather than crowd the range.
                break;
            }
            chosenCycles.add(newCyclesPerRF);
            frequenciesToTest.add(newCyclesPerRF / rfDiameter);
        }
    }

    /**
     * Draw a random cycles-per-RF value within [{@link #MIN_CYCLES_PER_RF},
     * {@link #MAX_CYCLES_PER_RF}] that is at least {@link #CYCLES_PER_RF_MARGIN} away from every
     * value in {@code existing}. Returns null if no such value is found within a fixed number of
     * attempts.
     */
    private Double sampleCyclesPerRFWithMargin(List<Double> existing) {
        double range = MAX_CYCLES_PER_RF - MIN_CYCLES_PER_RF;
        int maxAttempts = 1000;
        for (int attempt = 0; attempt < maxAttempts; attempt++) {
            double candidate = MIN_CYCLES_PER_RF + random.nextDouble() * range;
            boolean farEnough = true;
            for (Double value : existing) {
                if (Math.abs(candidate - value) < CYCLES_PER_RF_MARGIN) {
                    farEnough = false;
                    break;
                }
            }
            if (farEnough) {
                return candidate;
            }
        }
        return null;
    }

    private void addIsochromaticTrials() {
        IsoGaborSpec spec = new IsoGaborSpec(gaborSpec, "Gray");
        IsoGaborStim stim = new IsoGaborStim(this, spec);
//        getStims().add(stim);

        spec = new IsoGaborSpec(gaborSpec, "Red");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(gaborSpec, "Green");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(gaborSpec, "Cyan");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(gaborSpec, "Orange");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);
    }

    private void addIsoluminantTrials() {
        IsoGaborSpec spec = new IsoGaborSpec(gaborSpec, "CyanOrange");
        IsoGaborStim stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(gaborSpec, "RedGreen");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);
    }

    private void addMixedGaborTrials() {
        // Mixed Gabors - frequencies
        for (Double frequencyChromatic : frequencies) {
            GaborSpec chromaticSpec = new GaborSpec(gaborSpec);
            chromaticSpec.setFrequency(frequencyChromatic);
            for (Double frequencyLuminance : frequencies) {
                GaborSpec luminanceSpec = new GaborSpec(gaborSpec);
                luminanceSpec.setFrequency(frequencyLuminance);

                IsoGaborSpec rgMixedIsoSpec = new IsoGaborSpec(chromaticSpec, "RedGreen");
                MixedGaborStim rgMixedIsoStim = new MixedGaborStim(this, rgMixedIsoSpec, luminanceSpec);
                getStims().add(rgMixedIsoStim);

                IsoGaborSpec cyMixedIsoSpec = new IsoGaborSpec(chromaticSpec, "CyanOrange");
                MixedGaborStim cyMixedIsoStim = new MixedGaborStim(this, cyMixedIsoSpec, luminanceSpec);
                getStims().add(cyMixedIsoStim);
            }
        }

//        // Mixed Gabors - Phases
//        for (double frequency : frequencies) {
//            GaborSpec chromaticSpec = new GaborSpec(gaborSpec);
//            chromaticSpec.setFrequency(frequency);
//            for (double phase : mixedPhases) {
//                double phaseLuminance = phase * frequency;
//
//                GaborSpec luminanceSpec = new GaborSpec(gaborSpec);
//                luminanceSpec.setFrequency(frequency);
//                luminanceSpec.setPhase(phaseLuminance);
//
//                IsoGaborSpec rgMixedIsoSpec = new IsoGaborSpec(gaborSpec, "RedGreen");
//                MixedGaborStim rgMixedIsoStim = new MixedGaborStim(this, rgMixedIsoSpec, luminanceSpec);
//                getStims().add(rgMixedIsoStim);
//
//                IsoGaborSpec cyMixedIsoSpec = new IsoGaborSpec(gaborSpec, "CyanOrange");
//                MixedGaborStim cyMixedIsoStim = new MixedGaborStim(this, cyMixedIsoSpec, luminanceSpec);
//                getStims().add(cyMixedIsoStim);
//            }
//        }
    }

    @Override
    protected void writeTrials() {
        List<Long> allStimIds = new ArrayList<>();

        for (Stim stim : getStims()) {
            stim.writeStim();
            Long stimId = stim.getStimId();
            for (int i = 0; i < numRepeats; i++) {
                allStimIds.add(stimId);
            }
        }

        Collections.shuffle(allStimIds);

        long lastTaskId = -1L;
        for (Long stimId : allStimIds) {
            long taskId = getGlobalTimeUtil().currentTimeMicros();
            while (taskId == lastTaskId) {
                taskId = getGlobalTimeUtil().currentTimeMicros();
            }
            lastTaskId = taskId;

            getDbUtil().writeTaskToDo(taskId, stimId, -1, genId);
        }
    }


    private long getLatestTimestamp(JdbcTemplate jdbcTemplate, String table) {
        return (long) jdbcTemplate.queryForObject(
                "SELECT MAX(tstamp) FROM " + table + " WHERE channel = 'SUPRA-000'",
                Long.class
        );
    }

    private RFInfo getRFInfo(JdbcTemplate jdbcTemplate) {
        String rfInfoXml = (String) jdbcTemplate.queryForObject(
                "SELECT info FROM RFInfo WHERE tstamp = (" +
                        "    SELECT MAX(tstamp) FROM RFInfo WHERE channel = 'SUPRA-000'" +
                        ") AND channel = 'SUPRA-000' LIMIT 1",
                String.class
        );
        return RFInfo.fromXml(rfInfoXml);
    }

    private GaborSpec getStimSpec(JdbcTemplate jdbcTemplate) {
//        long latestTimestamp = getLatestTimestamp(jdbcTemplate, "RFObjectData");
        String stimSpecXml = (String) jdbcTemplate.queryForObject(
                "SELECT data FROM RFObjectData WHERE channel = 'SUPRA-000' AND object = 'org.xper.rfplot.drawing.gabor.Gabor' ORDER BY  tstamp DESC LIMIT 1",
                String.class
        );
        return GaborSpec.fromXml(stimSpecXml);
    }




}