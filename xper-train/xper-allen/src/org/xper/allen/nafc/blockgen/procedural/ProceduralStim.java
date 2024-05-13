package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.NAFCStim;
import org.xper.allen.nafc.blockgen.*;
import org.xper.allen.nafc.blockgen.psychometric.NAFCStimSpecWriter;
import org.xper.allen.nafc.experiment.RewardPolicy;
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

    protected Long taskId;

    @Override
    public void preWrite() {
        assignStimObjIds();
        generateMatchSticksAndSaveSpecs();
        drawPNGs();
        generateNoiseMap();
        assignCoords();
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
        stimObjIds = new Procedural<Long>(sampleId, matchId, proceduralDistractorIds, randDistractorIds);
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
            //Generate Sample
            ProceduralMatchStick sample = new ProceduralMatchStick();
            sample.setProperties(parameters.getSize(), parameters.textureType);
            sample.setStimColor(parameters.color);
            try {
                sample.genMatchStickFromComponentInNoise(baseMatchStick, morphComponentIndex, 0);
            } catch (ProceduralMatchStick.MorphRepetitionException e) {
                System.out.println("MorphRepetition FAILED: " + e.getMessage());
                continue;
            }

            mSticks.setSample(sample);
            mStickSpecs.setSample(mStickToSpec(sample, stimObjIds.getSample()));
            return sample;
        }
    }

    protected void generateMatch(ProceduralMatchStick sample) {
        //Generate Match
        mSticks.setMatch(sample);
        mStickSpecs.setMatch(mStickToSpec(sample, stimObjIds.getMatch()));
    }

    protected void generateProceduralDistractors(ProceduralMatchStick sample) {
        for (int i = 0; i < numProceduralDistractors; i++) {
            ProceduralMatchStick proceduralDistractor = new ProceduralMatchStick();
            proceduralDistractor.setProperties(parameters.getSize(), parameters.textureType);
            proceduralDistractor.setStimColor(parameters.color);
            proceduralDistractor.genNewComponentMatchStick(sample, morphComponentIndex, noiseComponentIndex, parameters.morphMagnitude, 0.5);
            mSticks.proceduralDistractors.add(proceduralDistractor);
            mStickSpecs.proceduralDistractors.add(mStickToSpec(proceduralDistractor, stimObjIds.proceduralDistractors.get(i)));
        }
    }

    protected void generateRandDistractors() {
        //Generate Rand Distractors
        for (int i = 0; i<numRandDistractors; i++) {
            ProceduralMatchStick randDistractor = new ProceduralMatchStick();
            randDistractor.setProperties(parameters.getSize(), parameters.textureType);
            randDistractor.setStimColor(parameters.color);
            randDistractor.genMatchStickRand();
            mSticks.randDistractors.add(randDistractor);
            mStickSpecs.randDistractors.add(mStickToSpec(randDistractor, stimObjIds.randDistractors.get(i)));
        }
    }

    protected AllenMStickSpec mStickToSpec(AllenMatchStick mStick, Long stimObjId) {
        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(mStick, true);
//        spec.writeInfo2File(generator.getGeneratorSpecPath() + "/" + stimObjId, true);
        return spec;
    }


    protected void drawPNGs() {
        AllenPNGMaker pngMaker = generator.getPngMaker();
        String generatorPngPath = generator.getGeneratorPngPath();

        drawSample(pngMaker, generatorPngPath);

        //Match
        List<String> matchLabels = Arrays.asList("match");
        String matchPath = pngMaker.createAndSavePNG(mSticks.getMatch(),stimObjIds.getMatch(), matchLabels, generatorPngPath);
        experimentPngPaths.setMatch(generator.convertPngPathToExperiment(matchPath));
        System.out.println("Match Path: " + matchPath);

        drawProceduralDistractors(pngMaker, generatorPngPath);

        //Rand Distractor
        List<String> randDistractorLabels = Arrays.asList("rand");
        for (int i = 0; i < numRandDistractors; i++) {
            String randDistractorPath = pngMaker.createAndSavePNG(mSticks.randDistractors.get(i),stimObjIds.randDistractors.get(i), randDistractorLabels, generatorPngPath);
            experimentPngPaths.addRandDistractor(generator.convertPngPathToExperiment(randDistractorPath));
            System.out.println("Rand Distractor Path: " + randDistractorPath);
        }
    }

    protected void drawProceduralDistractors(AllenPNGMaker pngMaker, String generatorPngPath) {
        //Procedural Distractors
        List<String> proceduralDistractorLabels = Arrays.asList("procedural");
        for (int i = 0; i < numProceduralDistractors; i++) {
            String proceduralDistractorPath = pngMaker.createAndSavePNG(mSticks.proceduralDistractors.get(i),stimObjIds.proceduralDistractors.get(i), proceduralDistractorLabels, generatorPngPath);
            experimentPngPaths.addProceduralDistractor(generator.convertPngPathToExperiment(proceduralDistractorPath));
            System.out.println("Procedural Distractor Path: " + proceduralDistractorPath);
        }
    }

    protected void drawSample(AllenPNGMaker pngMaker, String generatorPngPath) {
        //Sample
        List<String> sampleLabels = Arrays.asList("sample");
        String samplePath = pngMaker.createAndSavePNG(mSticks.getSample(),stimObjIds.getSample(), sampleLabels, generatorPngPath);
        System.out.println("Sample Path: " + samplePath);
        experimentPngPaths.setSample(generator.convertPngPathToExperiment(samplePath));
    }

    protected void generateNoiseMap() {
        System.out.println("Not Delta: Noise Component Index: " + noiseComponentIndex);
        List<String> noiseMapLabels = new LinkedList<>();
        noiseMapLabels.add("sample");
        String generatorNoiseMapPath = generator.getPngMaker().createAndSaveGaussNoiseMap(mSticks.getSample(), stimObjIds.getSample(), noiseMapLabels, generator.getGeneratorNoiseMapPath(), parameters.noiseChance, noiseComponentIndex);
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
            xCenter = coords.proceduralDistractors.get(i).getX();
            yCenter = coords.proceduralDistractors.get(i).getY();
            path = experimentPngPaths.proceduralDistractors.get(i);
            NoisyPngSpec proceduralDistractorSpec = new NoisyPngSpec(
                    xCenter, yCenter,
                    dimensions,
                    path,
                    noiseMapPath,
                    color);
            MStickStimObjData proceduralDistractorMStickObjData = new MStickStimObjData("procedural", mStickSpecs.proceduralDistractors.get(i));
            dbUtil.writeStimObjData(stimObjIds.proceduralDistractors.get(i), proceduralDistractorSpec.toXml(), proceduralDistractorMStickObjData.toXml());
        }

        //Rand Distractors
        for (int i = 0; i < numRandDistractors; i++) {
            xCenter = coords.randDistractors.get(i).getX();
            yCenter = coords.randDistractors.get(i).getY();
            path = experimentPngPaths.randDistractors.get(i);
            NoisyPngSpec randDistractorSpec = new NoisyPngSpec(
                    xCenter, yCenter,
                    dimensions,
                    path,
                    noiseMapPath,
                    color);
            MStickStimObjData randDistractorMStickObjData = new MStickStimObjData("rand", mStickSpecs.randDistractors.get(i));
            dbUtil.writeStimObjData(stimObjIds.randDistractors.get(i), randDistractorSpec.toXml(), randDistractorMStickObjData.toXml());
        }
    }

    protected void assignTaskId() {
        setTaskId(generator.getGlobalTimeUtil().currentTimeMicros());
    }

    protected void writeStimSpec(){
        NAFCStimSpecWriter stimSpecWriter = new NAFCStimSpecWriter(
                getStimId(),
                (AllenDbUtil) generator.getDbUtil(),
                parameters,
                coords,
                parameters.numChoices,
                stimObjIds, RewardPolicy.LIST, new int[]{0});

        stimSpecWriter.writeStimSpec();
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

        double noiseChance;
        int numChoices;
        int numRandDistractors;
        double morphMagnitude;
        double morphDiscreteness;
        Color color;
        double noiseRate = 1;
        String textureType;

        public ProceduralStimParameters() {
        }

        public ProceduralStimParameters(Lims sampleDistanceLims, Lims choiceDistanceLims, double size, double eyeWinSize, double noiseChance, int numChoices, int numRandDistractors, double morphMagnitude, double morphDiscreteness, Color color, String textureType) {
            super(sampleDistanceLims, choiceDistanceLims, size, eyeWinSize);
            this.noiseChance = noiseChance;
            this.numChoices = numChoices;
            this.numRandDistractors = numRandDistractors;
            this.morphMagnitude = morphMagnitude;
            this.morphDiscreteness = morphDiscreteness;
            this.color = color;
            this.textureType = textureType;
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

    }
}