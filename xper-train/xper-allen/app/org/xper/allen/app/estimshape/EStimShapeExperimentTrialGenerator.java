package org.xper.allen.app.estimshape;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.app.procedural.RadialSquares;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.noisy.NAFCNoiseMapper;
import org.xper.allen.drawing.ga.CircleReceptiveField;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.estimshape.EStimShapePsychometricTwoByTwoParameters;
import org.xper.allen.nafc.blockgen.estimshape.EStimShapePsychometricTwoByTwoStim;
import org.xper.allen.nafc.blockgen.procedural.*;
import org.xper.allen.nafc.blockgen.procedural.ProceduralStim.ProceduralStimParameters;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;

import javax.swing.*;
import java.awt.*;
import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.*;
import java.util.List;
import java.util.function.BiConsumer;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class EStimShapeExperimentTrialGenerator extends NAFCBlockGen {
    @Dependency
    String gaSpecPath;

    @Dependency
    ReceptiveFieldSource rfSource;

    @Dependency
    String generatorSetPath;

    @Dependency
    NAFCNoiseMapper noiseMapper;

    @Dependency
    AllenPNGMaker samplePngMaker;

    public static void main(String[] args) {
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (Exception e) {
            throw new XGLException(e);
        }

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));
        EStimShapeExperimentTrialGenerator generator = context.getBean(EStimShapeExperimentTrialGenerator.class);
        generator.generate();
    }

//    @Override
//    protected void addTrials() {

    @Override
    protected void init() {
//        super.init();
//        samplePngMaker.createDrawerWindow();
    }

    ////        addTrials_Deltas();
////        addTrials_ProceduralTwoByTwo();
//        addTrials_TwoByTwo_training();
//    }



    private void addTrials_TwoByTwo_training(){
        //input Parameters
        Color stimColor = new Color(0.5f, 0.5f, 0.5f);

        //Parameters
        //Num Repetitions of Each Condition
        int X = 1;
        double baseMagnitude = 1.5;
        double drivingMagnitude = 1.5;
        //Noise
        Map<Double, Integer> noiseConditions = new LinkedHashMap<>();
        noiseConditions.put(1.0, 1);
//        noiseConditions.put(0.1, 1);
//        noiseConditions.put(0.2, 1);
//        noiseConditions.put(0.3, 1);


        Map<String, Double> emphasizeChancesForConditions = new HashMap<>();

        HashMap<String, Integer> emphNumToRemoveForConditions = new HashMap<>();




        Map<String, Double> minimizeChancesForConditions = new HashMap<>();




        //ESTIM
        List<Boolean> isEStimEnabledConditions = new LinkedList<>();
//        isEStimEnabledConditions.add(true);
//        isEStimEnabledConditions.add(false);
//        isEStimEnabledConditions.add(false);
        isEStimEnabledConditions.add(false);

        //Delta Noise
        List<Boolean> isDeltaNoiseConditions = new LinkedList<>();
        isDeltaNoiseConditions.add(true);
        isDeltaNoiseConditions.add(false);

        //Assigning
        List<Path> paths = findSetSpecPaths(Paths.get(generatorSetPath));
        System.out.println(paths.size() + " paths found");

        Map<String, AllenMStickSpec> setConditions = new HashMap<>();
        for (Path path : paths) {
            String in_specStr;
            StringBuffer fileData = new StringBuffer(100000);
            try
            {
                BufferedReader reader = new BufferedReader(
                        new FileReader(path.toString()));
                char[] buf = new char[1024];
                int numRead=0;
                while((numRead=reader.read(buf)) != -1){
                    String readData = String.valueOf(buf, 0, numRead);
                    //System.out.println(readData);
                    fileData.append(readData);
                    buf = new char[1024];

                }
                reader.close();
            }
            catch (Exception e)
            {
                System.out.println("error in read XML spec file");
                System.out.println(e);
            }

            in_specStr = fileData.toString();
            setConditions.put(extractRomanNumeral(path.toString()), AllenMStickSpec.fromXml(in_specStr));
        }

        HashMap<String, AllenMStickSpec> sampleConditions = new HashMap<>(setConditions);


        //BIG LOOP - looping through all conditions

        //EStim Enabled or not
        for (Boolean isEStimEnabled: isEStimEnabledConditions) {

            //Sample
            for (String sampleCondition : sampleConditions.keySet()) {

                AllenMStickSpec sampleSpec = sampleConditions.get(sampleCondition);


                List<ProceduralStimParameters> behavioralTrialParams = assignTrialParams(
                        stimColor, noiseConditions);

                // Delta Noise
                for (Boolean isDeltaNoise: isDeltaNoiseConditions)
                {
                    //Noise Chance
                    for (ProceduralStimParameters proceduralStimParameters : behavioralTrialParams) {

                        //Calculate do emphasize for each condition
                        Map<String, Boolean> doEmphasizeConditionsForConditions = new HashMap<>();
                        for (String condition : emphasizeChancesForConditions.keySet()){
                            doEmphasizeConditionsForConditions.put(condition, emphasizeChancesForConditions.get(condition) > Math.random());
                        }

                        Map<String, AllenMStickSpec> baseProceduralDistractorSpecs =
                                new LinkedHashMap<>(setConditions);
                        baseProceduralDistractorSpecs.remove(sampleCondition);

                        //MANAGING BIASES
                        proceduralStimParameters.numRandDistractors = 0;
                        if (isEmphasize(sampleCondition, doEmphasizeConditionsForConditions)){
                            for (int i=0; i<emphNumToRemoveForConditions.get(sampleCondition); i++){

                                if (baseProceduralDistractorSpecs.isEmpty()){
                                    break;
                                }
                                //remove a random one
                                String randomKey = new ArrayList<>(baseProceduralDistractorSpecs.keySet()).get(
                                        (int) (Math.random() * baseProceduralDistractorSpecs.size())
                                );
                                baseProceduralDistractorSpecs.remove(randomKey);
                                proceduralStimParameters.numRandDistractors++;
                            }
                        }


                        //If minimize condition (i.e III) is NOT the current sample condition, don't include it as an option
                        for (String condition : minimizeChancesForConditions.keySet()){
                            if (!sampleCondition.equals(condition) && minimizeChancesForConditions.get(condition) > Math.random()){
                                if (baseProceduralDistractorSpecs.containsKey(condition)) {
                                    baseProceduralDistractorSpecs.remove(condition);
                                    proceduralStimParameters.numRandDistractors++;
                                }
                            }
                        }

                        //Repetitions for each condition
                        for (int i=0; i<X; i++) {
                            EStimShapePsychometricTwoByTwoStim behavioralTrial = new EStimShapePsychometricTwoByTwoStim(
                                    this,
                                    new EStimShapePsychometricTwoByTwoParameters(proceduralStimParameters,
                                            sampleSpec,
                                            baseProceduralDistractorSpecs,
                                            isEStimEnabled,
                                            sampleCondition,
                                            baseMagnitude,
                                            drivingMagnitude,
                                            isDeltaNoise));

                            stims.add(behavioralTrial);
                        }

                    }
                }
            }
        }

    }

    @Override
    public void shuffleTrials() {
        Collections.shuffle(stims);
//        Map<String, List<Stim>> groupedStims = new HashMap<String, List<Stim>>();
//        List<String> mainConditions = new ArrayList<String>();
//        List<Stim> otherStims = new ArrayList<Stim>();
//
//        // Group stims by set condition, separate out "other" stims
//        for (Stim stim : stims) {
//            if (stim instanceof EStimShapePsychometricTwoByTwoStim) {
//                String condition = ((EStimShapePsychometricTwoByTwoStim) stim).getSampleSetCondition();
//                if (!groupedStims.containsKey(condition)) {
//                    groupedStims.put(condition, new ArrayList<Stim>());
//                    mainConditions.add(condition);
//                }
//                groupedStims.get(condition).add(stim);
//            } else {
//                otherStims.add(stim);
//            }
//        }
//
//        List<Stim> shuffledStims = new ArrayList<Stim>();
//        boolean remaining = true;
//
//        // Distribute main condition stims
//        while (remaining) {
//            remaining = false;
//            Collections.shuffle(mainConditions);
//            for (String condition : mainConditions) {
//                List<Stim> conditionStims = groupedStims.get(condition);
//                if (!conditionStims.isEmpty()) {
//                    remaining = true;
//                    shuffledStims.add(conditionStims.remove(0));
//                }
//            }
//        }
//
//        // Randomly insert other stims
//        for (Stim otherStim : otherStims) {
//            int insertIndex = (int) (Math.random() * (shuffledStims.size() + 1));
//            shuffledStims.add(insertIndex, otherStim);
//        }
//
//        stims = shuffledStims;
    }

    private static boolean isEmphasize(String setCondition, Map<String, Boolean> doEmphasizeConditionsForConditions) {
        return doEmphasizeConditionsForConditions.containsKey(setCondition) && doEmphasizeConditionsForConditions.get(setCondition);
    }

    public static String extractRomanNumeral(String filePath) {
        // Pattern to match: any initial numbers, an underscore, more numbers, an underscore, Roman numerals, '_spec.xml'
        String pattern = "^(\\d+)_([\\d]+)_([IVXLCDM]+)_spec\\.xml$";
        Pattern compiledPattern = Pattern.compile(pattern);
        Matcher matcher = compiledPattern.matcher(Paths.get(filePath).getFileName().toString());

        if (matcher.matches()) {
            return matcher.group(3); // Group 3 is the Roman numeral
        } else {
            return null; // Return null if no match is found
        }
    }

    public static List<Path> findSetSpecPaths(Path directory) {
        List<Path> matchedFiles = new ArrayList<>();
        // Pattern to match: any initial numbers, an underscore, more numbers, an underscore, Roman numerals, '_spec.xml'
        String pattern = "^(\\d+)_([\\d]+)_([IVXLCDM]+)_spec\\.xml$";
        Pattern compiledPattern = Pattern.compile(pattern);

        try {
            Files.walkFileTree(directory, new SimpleFileVisitor<Path>() {
                @Override
                public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) throws IOException {
                    Matcher matcher = compiledPattern.matcher(file.getFileName().toString());
                    if (matcher.matches()) {
                        matchedFiles.add(file);
                    }
                    return FileVisitResult.CONTINUE;
                }
            });
        } catch (IOException e) {
            throw new RuntimeException(e);
        }

        return matchedFiles;
    }

    private void addTrials_ProceduralTwoByTwo(){
        //input Parameters
        Color stimColor = new Color(0.5f, 0.5f, 0.5f);
        long stimId = 1717531847398316L;
        int compId = 3;

        //Parameters
        Map<Double, Integer> numEStimTrialsForNoiseChances = new LinkedHashMap<>();
        numEStimTrialsForNoiseChances.put(0.5, 16);

        Map<Double, Integer> numBehavioralTrialsForNoiseChances = new LinkedHashMap<>();
        numBehavioralTrialsForNoiseChances.put(0.0, 3);
        numBehavioralTrialsForNoiseChances.put(0.05, 3);
        numBehavioralTrialsForNoiseChances.put(0.1, 3);
        numBehavioralTrialsForNoiseChances.put(0.2, 3);
        numBehavioralTrialsForNoiseChances.put(0.3, 3);
        numBehavioralTrialsForNoiseChances.put(0.4, 3);
        numBehavioralTrialsForNoiseChances.put(0.5, 3);
        numBehavioralTrialsForNoiseChances.put(1.0, 3);
        Map<Double, Integer> numTrainingTrialsForNoiseChances = new LinkedHashMap<>();
        numTrainingTrialsForNoiseChances.put(0.0, 0);

        List<ProceduralStimParameters> eStimTrialParams = assignTrialParams(
                stimColor, numEStimTrialsForNoiseChances);
        List<ProceduralStimParameters> behavioralTrialParams = assignTrialParams(
                stimColor, numBehavioralTrialsForNoiseChances);
        List<ProceduralStimParameters> trainingTrialParams = assignTrainingTrialParams(
                stimColor,
                numTrainingTrialsForNoiseChances,
                3);
        behavioralTrialParams.addAll(trainingTrialParams);


        List<Stim> eStimTrials = new LinkedList<>();
        //Add EStim Trials
        for (ProceduralStimParameters parameters : eStimTrialParams) {
            ProceduralMatchStick baseMStick = new ProceduralMatchStick(noiseMapper);
            baseMStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, rfSource.getRFRadiusDegrees()), "SHADE", 1.0);
            baseMStick.setStimColor(stimColor);
            baseMStick.genMatchStickFromFile(gaSpecPath + "/" + stimId + "_spec.xml");
            //using estim values set on the IntanGUI
            EStimShapeTwoByTwoStim eStimTrial = new EStimShapeTwoByTwoStim(
                    this,
                    parameters, baseMStick, compId, true,
                    0);
            EStimShapeTwoByTwoStim negativeControlTrial = new EStimShapeTwoByTwoStim(
                    this,
                    parameters, baseMStick, compId, false,
                    0);
            eStimTrials.add(eStimTrial);
//            eStimTrials.add(negativeControlTrial);
        }

        //Add Behavioral Trials
        List<ReceptiveField> behTrialRFs = assignRFsToBehTrials(eStimTrials.size(), 0, behavioralTrialParams.size(), getRF());

        List<Stim> behavioralTrials = new LinkedList<>();
        for (int i = 0; i< behavioralTrialParams.size(); i++){
            ProceduralStimParameters parameters = behavioralTrialParams.get(i);
            EStimShapeTwoByTwoBehavioralStim stim = new EStimShapeTwoByTwoBehavioralStim(
                    this, parameters,
                    behTrialRFs.get(i),
                    0);
            behavioralTrials.add(stim);
        }


        stims.addAll(behavioralTrials);
//        stims.addAll(eStimTrials);

    }

    private void addTrials_Deltas() {
        //input Parameters
        Color stimColor = new Color(0.5f, 0.5f, 0.5f);
        long stimId = 1717531847396095L;
        int compId = 2;

        //Parameters
        Map<Double, Integer> numEStimTrialsForNoiseChances = new LinkedHashMap<>();
        numEStimTrialsForNoiseChances.put(0.5, 5);

        int numDeltaSets = 0;

        Map<Double, Integer> numBehavioralTrialsForNoiseChances = new LinkedHashMap<>();
        numBehavioralTrialsForNoiseChances.put(0.5, 20);



        List<ProceduralStimParameters> eStimTrialParams = assignTrialParams(stimColor, numEStimTrialsForNoiseChances);
        List<ProceduralStimParameters> behavioralTrialParams = assignTrialParams(stimColor, numBehavioralTrialsForNoiseChances);

        //Make EStimTrials and Delta Trials
        List<Stim> eStimTrials = makeEStimProceduralTrials(eStimTrialParams, stimColor, stimId, compId);
        List<Stim> deltaTrials = makeDeltaTrials(numDeltaSets, eStimTrialParams, eStimTrials);

        //Assigning Fake RFS
        int numEStimTrials = eStimTrials.size();
        int numDeltaTrials = deltaTrials.size();
        int numBehavioralTrials = behavioralTrialParams.size();
        List<ReceptiveField> behTrialRFs = assignRFsToBehTrials(numEStimTrials, numDeltaTrials, numBehavioralTrials, getRF());

        List<Stim> behavioralTrials = makeBehavioralTrials(behavioralTrialParams, behTrialRFs);
        stims.addAll(behavioralTrials);
        stims.addAll(eStimTrials);
        stims.addAll(deltaTrials);

    }

    public static List<ReceptiveField> assignRFsToBehTrials(int numEStimTrials, int numDeltaTrials, int numBehavioralTrials, ReceptiveField realRf) {
        int numTestTrials = numEStimTrials + numDeltaTrials;
        int numTotalTrials = numTestTrials + numBehavioralTrials;
        int numToDistributeToFakeRFs = numTotalTrials - (2*numTestTrials);
        double numRFs = (double) numTotalTrials / numToDistributeToFakeRFs;
        if (numRFs % 1 != 0){
            throw new IllegalArgumentException("Number of Behavioral Trials must be a multiple of the number of EStimTrials and DeltaTrials");
        }
        int numFakeRFs = (int) (numRFs - 1); //minus one for the real one
        int numTrialsPerRF = (int) (numTotalTrials/numRFs);
        double eccentricity = realRf.getCenter().distance(new Coordinates2D(0, 0));
        double angleDf = 360.0 / numRFs;

        double realRFAngle = RFUtils.cartesianToPolarAngle(realRf.getCenter());
        Set<ReceptiveField> fakeRFs = new HashSet<>();
        for (int i = 1; i <= numFakeRFs; i++){
            double angle = realRFAngle + angleDf * i;
            Coordinates2D fakeCenter = RFUtils.polarToCartesian(eccentricity, angle);
            ReceptiveField fakeRF = new CircleReceptiveField(fakeCenter, realRf.radius);
            fakeRFs.add(fakeRF);
        }

        List<ReceptiveField> behTrialRFs = new LinkedList<>();
        //Assign To Fake RFs
        fakeRFs.forEach(new java.util.function.Consumer<ReceptiveField>() {
                            @Override
                            public void accept(ReceptiveField fakeRF) {
                                for (int i = 0; i < numTrialsPerRF; i++){
                                    behTrialRFs.add(fakeRF);
                                }
                            }
                        }
        );
        //Assign to Real RF
        for (int i=0; i<numTrialsPerRF/2; i++){
            behTrialRFs.add(realRf);
        }
        return behTrialRFs;
    }

    private List<Stim> makeEStimProceduralTrials(List<ProceduralStimParameters> eStimTrialParams, Color stimColor, long stimId, int compId) {
        List<Stim> eStimTrials = new LinkedList<>();
        //Add EStim Trials
        for (ProceduralStimParameters parameters : eStimTrialParams) {
            ProceduralMatchStick baseMStick = new ProceduralMatchStick(noiseMapper);
            baseMStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, rfSource.getRFRadiusDegrees()), "SHADE", 1.0);
            baseMStick.setStimColor(stimColor);
            baseMStick.genMatchStickFromFile(gaSpecPath + "/" + stimId + "_spec.xml");
            //using estim values set on the IntanGUI
            EStimShapeProceduralStim eStimTrial = new EStimShapeProceduralStim(
                    this,
                    parameters, baseMStick, compId, true, stimId, compId);
            EStimShapeProceduralStim negativeControlTrial = new EStimShapeProceduralStim(
                    this,
                    parameters, baseMStick, compId, false, stimId, compId);
            eStimTrials.add(eStimTrial);
            eStimTrials.add(negativeControlTrial);
        }
        return eStimTrials;
    }

    private static List<Stim> makeDeltaTrials(int numDeltaSets, List<ProceduralStimParameters> eStimTrialParams, List<Stim> eStimTrials) {
        //Add Delta Trials
        List<Stim> deltaTrials = new LinkedList<>();
        for (int i = 0; i< numDeltaSets; i++){
            int randIndex = (int) (Math.random() * eStimTrialParams.size());
            EStimShapeProceduralStim baseStim = (EStimShapeProceduralStim) eStimTrials.get(randIndex);
            EStimShapeDeltaStim deltaMorph = new EStimShapeDeltaStim(baseStim, true, false);
            EStimShapeDeltaStim deltaNoise = new EStimShapeDeltaStim(baseStim, false, true);
            EStimShapeDeltaStim deltaBoth = new EStimShapeDeltaStim(baseStim, true, true);
            deltaTrials.add(deltaMorph);
            deltaTrials.add(deltaNoise);
            deltaTrials.add(deltaBoth);
        }
        return deltaTrials;
    }

    private List<Stim> makeBehavioralTrials(List<ProceduralStimParameters> behavioralTrialParams, List<ReceptiveField> fakeRFs) {
        //Add Behavioral Trials
        List<Stim> behavioralTrials = new LinkedList<>();
        for (int i = 0; i< behavioralTrialParams.size(); i++){
            ProceduralStimParameters parameters = behavioralTrialParams.get(i);
            EStimShapeProceduralBehavioralStim stim = new EStimShapeProceduralBehavioralStim(this, parameters, fakeRFs.get(i));
            behavioralTrials.add(stim);
        }

        return behavioralTrials;
    }

    private List<ProceduralStimParameters> assignTrialParams(Color stimColor, Map<Double, Integer> numTrialsForNoiseChances) {
        //Specifying universal parameters
        double eyeWinRadius = calculateEyeWinRadius();
        int numChoices = 4;
        double choiceRadius = RadialSquares.calculateRequiredRadius(
                numChoices,
                eyeWinRadius,
                eyeWinRadius/1.5);

        //Init EStim Trial Parameters
        List<ProceduralStimParameters> eStimTrialParams = new LinkedList<>();
        numTrialsForNoiseChances.forEach(new BiConsumer<Double, Integer>() {
            @Override
            public void accept(Double noiseChance, Integer numTrials) {

                for (int i = 0; i < numTrials; i++) {

                    ProceduralStimParameters parameters = new ProceduralStimParameters(
                            new Lims(0, 0),
                            new Lims(choiceRadius, choiceRadius),
                            getImageDimensionsDegrees(),
                            eyeWinRadius,
                            noiseChance,
                            numChoices,
                            0,
                            0.7,
                            0.5,
                            stimColor,
                            "SHADE",
                            0.5);


                    eStimTrialParams.add(parameters);
                }
            }
        });
        return eStimTrialParams;
    }

    private List<ProceduralStimParameters> assignTrainingTrialParams(Color stimColor, Map<Double, Integer> numTrialsForNoiseChances, int numChoices) {
        //Specifying universal parameters
        double eyeWinRadius = calculateEyeWinRadius();
        double choiceRadius = RadialSquares.calculateRequiredRadius(
                numChoices,
                eyeWinRadius,
                eyeWinRadius/1.5);

        //Init EStim Trial Parameters
        List<ProceduralStimParameters> eStimTrialParams = new LinkedList<>();
        numTrialsForNoiseChances.forEach(new BiConsumer<Double, Integer>() {
            @Override
            public void accept(Double noiseChance, Integer numTrials) {

                for (int i = 0; i < numTrials; i++) {

                    ProceduralStimParameters parameters = new ProceduralStimParameters(
                            new Lims(0, 0),
                            new Lims(choiceRadius, choiceRadius),
                            getImageDimensionsDegrees() * 0.9, //not used?
                            eyeWinRadius,
                            noiseChance,
                            numChoices,
                            0,
                            0.5,
                            0.5,
                            stimColor,
                            "SHADE",
                            1);

                    eStimTrialParams.add(parameters);
                }
            }
        });
        return eStimTrialParams;
    }

    private double calculateEyeWinRadius() {
        double shapeSquareLength = RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, rfSource.getRFRadiusDegrees());
        double squareDiagonal = Math.sqrt(2) * shapeSquareLength;
        double eyeWinRadius = squareDiagonal /2;
        return eyeWinRadius;
    }

    public ReceptiveField getRF() {
        return rfSource.getReceptiveField();
    }

    public String getGaSpecPath() {
        return gaSpecPath;
    }

    public void setGaSpecPath(String gaSpecPath) {
        this.gaSpecPath = gaSpecPath;
    }

    public ReceptiveFieldSource getRfSource() {
        return rfSource;
    }

    public void setRfSource(ReceptiveFieldSource rfSource) {
        this.rfSource = rfSource;
    }

    public String getGeneratorSetPath() {
        return generatorSetPath;
    }

    public void setGeneratorSetPath(String generatorSetPath) {
        this.generatorSetPath = generatorSetPath;
    }

    public NAFCNoiseMapper getNoiseMapper() {
        return noiseMapper;
    }

    public void setNoiseMapper(NAFCNoiseMapper noiseMapper) {
        this.noiseMapper = noiseMapper;
    }

    public AllenPNGMaker getSamplePngMaker() {
        return samplePngMaker;
    }

    public void setSamplePngMaker(AllenPNGMaker samplePngMaker) {
        this.samplePngMaker = samplePngMaker;
    }
}