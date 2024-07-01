package org.xper.allen.app.estimshape;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.app.procedural.RadialSquares;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.ga.CircleReceptiveField;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.estimshape.EStimShapeTwoByTwoStim;
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

public class EStimExperimentTrialGenerator extends NAFCBlockGen {
    @Dependency
    String gaSpecPath;

    @Dependency
    ReceptiveFieldSource rfSource;

    @Dependency
    String generatorSetPath;

    public static void main(String[] args) {
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (Exception e) {
            throw new XGLException(e);
        }

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));
        EStimExperimentTrialGenerator generator = context.getBean(EStimExperimentTrialGenerator.class);
        generator.generate();
    }

    @Override
    public void shuffleTrials() {
        Collections.shuffle(stims);
    }

    @Override
    protected void addTrials() {
//        addTrials_Deltas();
//        addTrials_ProceduralTwoByTwo();
        addTrials_TwoByTwo();
    }

    private void addTrials_TwoByTwo(){
        //input Parameters
        Color stimColor = new Color(0.5f, 0.5f, 0.5f);

        //Parameters
        Map<Double, Integer> numBehavioralTrialsForNoiseChances = new LinkedHashMap<>();
        numBehavioralTrialsForNoiseChances.put(1.0, 1);


        //Assigning
        List<Path> paths = findSetSpecPaths(Paths.get(generatorSetPath));
        System.out.println(paths.size() + " paths found");

        Set<AllenMStickSpec> mStickSet = new HashSet<>();
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
            mStickSet.add(AllenMStickSpec.fromXml(in_specStr));
        }

        System.out.println(mStickSet.size() + " specs found");


        for (AllenMStickSpec sampleSpec : mStickSet) {
            Set<AllenMStickSpec> baseProceduralDistractorSpecs = new HashSet<>(mStickSet);
            baseProceduralDistractorSpecs.remove(sampleSpec);


            List<ProceduralStimParameters> behavioralTrialParams = assignTrialParams(
                    stimColor, numBehavioralTrialsForNoiseChances);

            for (ProceduralStimParameters parameters : behavioralTrialParams) {
                EStimShapeTwoByTwoStim behavioralTrial = new EStimShapeTwoByTwoStim(
                        this,
                        parameters,
                        sampleSpec,
                        baseProceduralDistractorSpecs
                );

            stims.add(behavioralTrial);

            }
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
        long stimId = 1717531847396095L;
        int compId = 2;

        //Parameters
        Map<Double, Integer> numEStimTrialsForNoiseChances = new LinkedHashMap<>();
        numEStimTrialsForNoiseChances.put(0.5, 30);

        Map<Double, Integer> numBehavioralTrialsForNoiseChances = new LinkedHashMap<>();
        numBehavioralTrialsForNoiseChances.put(0.1, 10);
        numBehavioralTrialsForNoiseChances.put(0.2, 10);
        numBehavioralTrialsForNoiseChances.put(0.3, 10);
        numBehavioralTrialsForNoiseChances.put(0.4, 10);
        numBehavioralTrialsForNoiseChances.put(0.5, 5);
        numBehavioralTrialsForNoiseChances.put(0.6, 5);
        numBehavioralTrialsForNoiseChances.put(0.7, 5);
        numBehavioralTrialsForNoiseChances.put(1.0, 5);
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
            ProceduralMatchStick baseMStick = new ProceduralMatchStick();
            baseMStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, rfSource), "SHADE");
            baseMStick.setStimColor(stimColor);
            baseMStick.genMatchStickFromFile(gaSpecPath + "/" + stimId + "_spec.xml");
            //using estim values set on the IntanGUI
            EStimShapeProceduralTwoByTwoStim eStimTrial = new EStimShapeProceduralTwoByTwoStim(
                    this,
                    parameters, baseMStick, compId, true,
                    0);
            EStimShapeProceduralTwoByTwoStim negativeControlTrial = new EStimShapeProceduralTwoByTwoStim(
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
            EStimShapeProceduralTwoByTwoBehavioralStim stim = new EStimShapeProceduralTwoByTwoBehavioralStim(
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
            ProceduralMatchStick baseMStick = new ProceduralMatchStick();
            baseMStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, rfSource), "SHADE");
            baseMStick.setStimColor(stimColor);
            baseMStick.genMatchStickFromFile(gaSpecPath + "/" + stimId + "_spec.xml");
            //using estim values set on the IntanGUI
            EStimShapeProceduralStim eStimTrial = new EStimShapeProceduralStim(
                    this,
                    parameters, baseMStick, compId, true);
            EStimShapeProceduralStim negativeControlTrial = new EStimShapeProceduralStim(
                    this,
                    parameters, baseMStick, compId, false);
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
                            getImageDimensionsDegrees() * 0.95,
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
        double shapeSquareLength = RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, rfSource);
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
}