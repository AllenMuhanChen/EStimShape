package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.NAFCStim;
import org.xper.allen.nafc.blockgen.*;
import org.xper.allen.nafc.blockgen.psychometric.NAFCStimSpecWriter;
import org.xper.allen.nafc.vo.MStickStimObjData;

import org.xper.allen.specs.NoisyPngSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.time.TimeUtil;

import java.awt.*;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;

public class ProceduralStim implements NAFCStim {
    //Input
    protected final NAFCBlockGen generator;
    protected ProceduralStimParameters parameters;
    protected ProceduralMatchStick baseMatchStick;
    protected int morphComponentIndex;
    protected int noiseComponentIndex;


    public ProceduralStim(NAFCBlockGen generator,
                          ProceduralStimParameters parameters,
                          ProceduralMatchStick baseMatchStick,
                          int morphComponentIndex) {
        this.generator = generator;
        this.parameters = parameters;
        this.baseMatchStick = baseMatchStick;
        this.morphComponentIndex = morphComponentIndex;
    }

    //Local Vars
    protected Procedural<Long> stimObjIds = new Procedural<>();
    protected Procedural<ProceduralMatchStick> mSticks = new Procedural<>();
    protected Procedural<AllenMStickSpec> mStickSpecs = new Procedural<>();
    protected int numProceduralDistractors;
    protected int numRandDistractors;
    protected Procedural<String> experimentPngPaths = new Procedural<>();
    protected String experimentNoiseMapPath;
    protected Procedural<Coordinates2D> coords = new Procedural<>();
    protected Procedural<List<String>> labels = new Procedural<>();

    protected Long taskId;

    @Override
    public void preWrite() {
        assignStimObjIds();
        assignLabels();
        generateMatchSticksAndSaveSpecs();
        drawPNGs();
        generateNoiseMap();
        assignCoords();
    }

    protected void assignLabels() {
        labels.setSample(new LinkedList<>(Arrays.asList("sample")));
        labels.setMatch(new LinkedList<>(Arrays.asList("match")));
        for (int i = 0; i < numProceduralDistractors; i++) {
            labels.addProceduralDistractor(new LinkedList<>(Arrays.asList("procedural")));
        }
        for (int i = 0; i < numRandDistractors; i++) {
            labels.addRandDistractor(new LinkedList<>(Arrays.asList("rand")));
        }
    }

    @Override
    public void writeStim() {
        writeStimObjDataSpecs();
        assignTaskId();
        writeStimSpec();
    }



    protected void assignStimObjIds() {
        TimeUtil timeUtil = generator.getGlobalTimeUtil();
        long sampleId = timeUtil.currentTimeMicros();
        long matchId = sampleId + 1;
        numRandDistractors = parameters.numRandDistractors;
        numProceduralDistractors = parameters.numChoices - numRandDistractors - 1;
        List<Long> proceduralDistractorIds = new LinkedList<>();
        for (int i = 0; i < numProceduralDistractors; i++) {
            proceduralDistractorIds.add(matchId + i + 1);
        }
        List<Long> randDistractorIds = new LinkedList<>();
        for (int i = 0; i < numRandDistractors; i++) {
            randDistractorIds.add(matchId + i + 1 + numProceduralDistractors);
        }
        stimObjIds = new Procedural<>(sampleId, matchId, proceduralDistractorIds, randDistractorIds);
    }

    protected void generateMatchSticksAndSaveSpecs() {
        ProceduralMatchStick sample = generateSample();

        noiseComponentIndex = sample.getDrivingComponent();

        generateMatch(sample);

        generateProceduralDistractors(sample);

        generateRandDistractors();
    }

    protected ProceduralMatchStick generateSample() {
        while (true) {
            System.out.println("Trying to generate sample for ProceduralStim");
            //Generate Sample
            ProceduralMatchStick sample = new ProceduralMatchStick(generator.getPngMaker().getNoiseMapper());
            sample.setProperties(parameters.getSize(), parameters.textureType);
            sample.setStimColor(parameters.color);
            try {
                sample.genMatchStickFromComponentInNoise(baseMatchStick, morphComponentIndex, 0, true, sample.maxAttempts, generator.getPngMaker().getNoiseMapper());
            } catch (ProceduralMatchStick.MorphRepetitionException e) {
                System.out.println("MorphRepetition FAILED: " + e.getMessage());
                continue;
            }

            mSticks.setSample(sample);
            mStickSpecs.setSample(mStickToSpec(sample));
            return sample;
        }
    }

    protected void generateMatch(ProceduralMatchStick sample) {
        //Generate Match
        mSticks.setMatch(sample);
        mStickSpecs.setMatch(mStickToSpec(sample));
    }

    protected void generateProceduralDistractors(ProceduralMatchStick sample) {
        for (int i = 0; i < numProceduralDistractors; i++) {
            ProceduralMatchStick proceduralDistractor = new ProceduralMatchStick(generator.getPngMaker().getNoiseMapper());
            proceduralDistractor.setProperties(parameters.getSize(), parameters.textureType);
            proceduralDistractor.setStimColor(parameters.color);
            proceduralDistractor.genNewComponentMatchStick(sample, morphComponentIndex, parameters.morphMagnitude, 0.5, true, proceduralDistractor.maxAttempts);
            mSticks.addProceduralDistractor(proceduralDistractor);
            mStickSpecs.addProceduralDistractor(mStickToSpec(proceduralDistractor));
        }
    }

    protected void generateRandDistractors() {
        //Generate Rand Distractors
        for (int i = 0; i<numRandDistractors; i++) {
            ProceduralMatchStick randDistractor = new ProceduralMatchStick(generator.getPngMaker().getNoiseMapper());
            randDistractor.setProperties(parameters.getSize(), parameters.textureType);
            randDistractor.setStimColor(parameters.color);
            randDistractor.genMatchStickRand();
            mSticks.addRandDistractor(randDistractor);
            mStickSpecs.addRandDistractor(mStickToSpec(randDistractor));
        }
    }

    protected AllenMStickSpec mStickToSpec(AllenMatchStick mStick) {
        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(mStick, false);
//        spec.writeInfo2File(generator.getGeneratorSpecPath() + "/" + stimObjId, true);
        return spec;
    }


    protected void drawPNGs() {
        AllenPNGMaker pngMaker = generator.getPngMaker();
        String generatorPngPath = generator.getGeneratorPngPath();

        drawSample(pngMaker, generatorPngPath);

        //Match
        String matchPath = pngMaker.createAndSavePNG(mSticks.getMatch(),stimObjIds.getMatch(), labels.getMatch(), generatorPngPath);
        experimentPngPaths.setMatch(generator.convertPngPathToExperiment(matchPath));
        System.out.println("Match Path: " + matchPath);

        drawProceduralDistractors(pngMaker, generatorPngPath);

        //Rand Distractor
        for (int i = 0; i < numRandDistractors; i++) {
            String randDistractorPath = pngMaker.createAndSavePNG(mSticks.getRandDistractors().get(i), stimObjIds.getRandDistractors().get(i), labels.getRandDistractors().get(i), generatorPngPath);
            experimentPngPaths.addRandDistractor(generator.convertPngPathToExperiment(randDistractorPath));
            System.out.println("Rand Distractor Path: " + randDistractorPath);
        }
    }

    protected void drawProceduralDistractors(AllenPNGMaker pngMaker, String generatorPngPath) {
        //Procedural Distractors
        for (int i = 0; i < numProceduralDistractors; i++) {
            String proceduralDistractorPath = pngMaker.createAndSavePNG(mSticks.getProceduralDistractors().get(i), stimObjIds.getProceduralDistractors().get(i), labels.getProceduralDistractors().get(i), generatorPngPath);
            experimentPngPaths.addProceduralDistractor(generator.convertPngPathToExperiment(proceduralDistractorPath));
            System.out.println("Procedural Distractor Path: " + proceduralDistractorPath);
        }
    }

    protected void drawSample(AllenPNGMaker pngMaker, String generatorPngPath) {
        //Sample
        String samplePath = pngMaker.createAndSavePNG(mSticks.getSample(),stimObjIds.getSample(), labels.getSample(), generatorPngPath);
        System.out.println("Sample Path: " + samplePath);
        experimentPngPaths.setSample(generator.convertPngPathToExperiment(samplePath));
    }

    protected void generateNoiseMap() {
        String generatorNoiseMapPath = generator.getPngMaker().createAndSaveNoiseMap(
                mSticks.getSample(),
                stimObjIds.getSample(),
                labels.getSample(),
                generator.getGeneratorNoiseMapPath(),
                parameters.noiseChance, noiseComponentIndex);
        experimentNoiseMapPath = generator.convertGeneratorNoiseMapToExperiment(generatorNoiseMapPath);
    }

    protected void assignCoords() {

        class ProceduralCoordinateAssigner extends NAFCCoordinateAssigner{

            private final int numProceduralDistractors;
            private final int numRandDistractors;


            public ProceduralCoordinateAssigner(int numChoices, Lims sampleDistanceLims, Lims choiceDistanceLims, int numProceduralDistractors, int numRandDistractors) {
                super(numChoices, sampleDistanceLims, choiceDistanceLims);
                this.numProceduralDistractors = numProceduralDistractors;
                this.numRandDistractors = numRandDistractors;
                assignCoords();
            }

            @Override
            protected void assignDistractorCoords() {
                List<Coordinates2D> allDistractors = ddUtil.getDistractorCoordsAsList();
                for (int i = 0; i < numProceduralDistractors; i++) {
                    getCoords().addProceduralDistractor(allDistractors.get(i));
                }
                for (int i = 0; i < numRandDistractors; i++) {
                    getCoords().addRandDistractor(allDistractors.get(i + numProceduralDistractors));
                }
            }

            @Override
            public Procedural<Coordinates2D> getCoords() {
                return coords;
            }
        }

        ProceduralCoordinateAssigner assigner = new ProceduralCoordinateAssigner(
                parameters.numChoices,
                parameters.getSampleDistanceLims(),
                parameters.getChoiceDistanceLims(),
                numProceduralDistractors,
                numRandDistractors);

        coords = assigner.getCoords();
    }

    protected void writeStimObjDataSpecs() {
        //Sample
        double xCenter = coords.getSample().getX();
        double yCenter = coords.getSample().getY();
        double imageSize = generator.getImageDimensionsDegrees();
        ImageDimensions dimensions = new ImageDimensions(imageSize, imageSize);
        String path = experimentPngPaths.getSample();
        String noiseMapPath = experimentNoiseMapPath;
        Color color = parameters.color;
        double numNoiseFrames = parameters.noiseRate;
        NoisyPngSpec sampleSpec = new NoisyPngSpec(
                xCenter, yCenter,
                dimensions,
                path,
                noiseMapPath,
                color,
                numNoiseFrames,
                parameters.noiseChance);
        MStickStimObjData sampleMStickObjData = new MStickStimObjData("sample", mStickSpecs.getSample());
        AllenDbUtil dbUtil = (AllenDbUtil) generator.getDbUtil();
        dbUtil.writeStimObjData(stimObjIds.getSample(), sampleSpec.toXml(), sampleMStickObjData.toXml());

        //Match
        xCenter = coords.getMatch().getX();
        yCenter = coords.getMatch().getY();
        path = experimentPngPaths.getMatch();
        noiseMapPath = "";
        NoisyPngSpec matchSpec = new NoisyPngSpec(
                xCenter, yCenter,
                dimensions,
                path,
                noiseMapPath,
                color);
        MStickStimObjData matchMStickObjData = new MStickStimObjData("match", mStickSpecs.getMatch());
        dbUtil.writeStimObjData(stimObjIds.getMatch(), matchSpec.toXml(), matchMStickObjData.toXml());

        //Procedural Distractors
        for (int i = 0; i < numProceduralDistractors; i++) {
            xCenter = coords.getProceduralDistractors().get(i).getX();
            yCenter = coords.getProceduralDistractors().get(i).getY();
            path = experimentPngPaths.getProceduralDistractors().get(i);
            NoisyPngSpec proceduralDistractorSpec = new NoisyPngSpec(
                    xCenter, yCenter,
                    dimensions,
                    path,
                    noiseMapPath,
                    color);
            MStickStimObjData proceduralDistractorMStickObjData = new MStickStimObjData("procedural", mStickSpecs.getProceduralDistractors().get(i));
            dbUtil.writeStimObjData(stimObjIds.getProceduralDistractors().get(i), proceduralDistractorSpec.toXml(), proceduralDistractorMStickObjData.toXml());
        }

        //Rand Distractors
        for (int i = 0; i < numRandDistractors; i++) {
            xCenter = coords.getRandDistractors().get(i).getX();
            yCenter = coords.getRandDistractors().get(i).getY();
            path = experimentPngPaths.getRandDistractors().get(i);
            NoisyPngSpec randDistractorSpec = new NoisyPngSpec(
                    xCenter, yCenter,
                    dimensions,
                    path,
                    noiseMapPath,
                    color);
            MStickStimObjData randDistractorMStickObjData = new MStickStimObjData("rand", mStickSpecs.getRandDistractors().get(i));
            dbUtil.writeStimObjData(stimObjIds.getRandDistractors().get(i), randDistractorSpec.toXml(), randDistractorMStickObjData.toXml());
        }
    }

    protected void assignTaskId() {
        setTaskId(generator.getGlobalTimeUtil().currentTimeMicros());
    }

    protected void writeStimSpec(){
        RewardBehavior rewardBehavior = specifyRewardBehavior();
        NAFCStimSpecWriter stimSpecWriter = NAFCStimSpecWriter.createForNoEStim(
                this.getClass().getSimpleName(), getStimId(),
                (AllenDbUtil) generator.getDbUtil(),
                parameters,
                coords,
                parameters.numChoices,
                stimObjIds,
                rewardBehavior.rewardPolicy,
                rewardBehavior.rewardList
        );

        stimSpecWriter.writeStimSpec();
    }


    @Override
    public RewardBehavior specifyRewardBehavior() {
        return RewardBehaviors.rewardMatchOnly();
    }


    protected void setTaskId(Long sample) {
        this.taskId = sample;
    }

    @Override
    public Long getStimId() {
        return taskId;
    }

    @Override
    public ProceduralStimParameters getParameters() {
        return parameters;
    }

    public static class ProceduralStimParameters extends NAFCTrialParameters{

        public double noiseChance;
        public int numChoices;
        public int numRandDistractors;
        public double morphMagnitude;
        public double morphDiscreteness;
        public Color color;
        public double noiseRate = 1;
        public String textureType;

        public ProceduralStimParameters() {
        }

        public ProceduralStimParameters(Lims sampleDistanceLims, Lims choiceDistanceLims, double size, double eyeWinSize, double noiseChance, int numChoices, int numRandDistractors, double morphMagnitude, double morphDiscreteness, Color color, String textureType, double noiseRate) {
            super(sampleDistanceLims, choiceDistanceLims, size, eyeWinSize);
            this.noiseChance = noiseChance;
            this.numChoices = numChoices;
            this.numRandDistractors = numRandDistractors;
            this.morphMagnitude = morphMagnitude;
            this.morphDiscreteness = morphDiscreteness;
            this.color = color;
            this.textureType = textureType;
            this.noiseRate = noiseRate;
        }

        public ProceduralStimParameters(NAFCTrialParameters other, double noiseChance, double noiseRate, int numChoices, int numRandDistractors, double morphMagnitude, double morphDiscreteness, Color color, String textureType) {
            super(other);
            this.noiseChance = noiseChance;
            this.noiseRate = noiseRate;
            this.numChoices = numChoices;
            this.numRandDistractors = numRandDistractors;
            this.morphMagnitude = morphMagnitude;
            this.morphDiscreteness = morphDiscreteness;
            this.color = color;
            this.textureType = textureType;
        }

        public ProceduralStimParameters(ProceduralStimParameters other) {
            super(other);
            this.noiseChance = other.noiseChance;
            this.numChoices = other.numChoices;
            this.numRandDistractors = other.numRandDistractors;
            this.morphMagnitude = other.morphMagnitude;
            this.morphDiscreteness = other.morphDiscreteness;
            this.color = other.color;
            this.noiseRate = other.noiseRate;
            this.textureType = other.textureType;
        }
    }
}