package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.ExperimentMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.blockgen.*;
import org.xper.allen.nafc.blockgen.psychometric.NAFCStimSpecWriter;
import org.xper.allen.nafc.vo.MStickStimObjData;

import org.xper.allen.specs.NoisyPngSpec;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.time.TimeUtil;

import java.awt.*;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;

public class ProceduralStim implements Stim {
    //Input
    private AbstractMStickPngTrialGenerator generator;
    ProceduralStimParameters parameters;
    ExperimentMatchStick baseMatchStick;
    int drivingComponent;

    //Local Vars
    Procedural<Long> stimObjIds;
    Procedural<ProceduralMatchStick> mSticks;
    Procedural<AllenMStickSpec> mStickSpecs;
    private int numProceduralDistractors;
    private int numRandDistractors;
    private Procedural<String> experimentPngPaths;
    private String experimentNoiseMapPath;
    private Procedural<Coordinates2D> coords;
    private Long taskId;

    public ProceduralStim(AbstractMStickPngTrialGenerator generator, ProceduralStimParameters parameters, ExperimentMatchStick baseMatchStick, int drivingComponent) {
        this.generator = generator;
        this.parameters = parameters;
        this.baseMatchStick = baseMatchStick;
        this.drivingComponent = drivingComponent;
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        assignStimObjIds();
        generateMatchSticks();
        drawPNGs();
        generateNoiseMap();
        assignCoords();
        writeStimObjDataSpecs();
        assignTaskId();
        writeStimSpec();
    }

    private void assignStimObjIds() {
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

    private void generateMatchSticks() {
        //Generate Sample
        ProceduralMatchStick sample = new ProceduralMatchStick();
        sample.setProperties(generator.getMaxImageDimensionDegrees());
        sample.setStimColor(parameters.color);
        sample.genMatchStickFromDrivingComponent(baseMatchStick, drivingComponent);
        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));

        //Generate Match
        mSticks.setMatch(sample);
        mStickSpecs.setMatch(mStickToSpec(sample));

        //Generate Procedural Distractors
        for (int i = 0; i < numProceduralDistractors; i++) {
            ProceduralMatchStick proceduralDistractor = new ProceduralMatchStick();
            proceduralDistractor.setProperties(generator.getMaxImageDimensionDegrees());
            proceduralDistractor.setStimColor(parameters.color);
            proceduralDistractor.genNewDrivingComponentMatchStick(sample, drivingComponent, parameters.morphMagnitude);
            mSticks.proceduralDistractors.add(proceduralDistractor);
            mStickSpecs.proceduralDistractors.add(mStickToSpec(proceduralDistractor));
        }

        //Generate Rand Distractors
        for (int i = 0; i<numRandDistractors; i++) {
            ProceduralMatchStick randDistractor = new ProceduralMatchStick();
            randDistractor.setProperties(generator.getMaxImageDimensionDegrees());
            randDistractor.setStimColor(parameters.color);
            randDistractor.genMatchStickRand();
            mSticks.randDistractors.add(randDistractor);
            mStickSpecs.randDistractors.add(mStickToSpec(randDistractor));
        }
    }

    private AllenMStickSpec mStickToSpec(AllenMatchStick mStick) {
        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(mStick);
        return spec;
    }

    private void drawPNGs() {
        AllenPNGMaker pngMaker = new AllenPNGMaker();
        String generatorPngPath = generator.getGeneratorPngPath();

        pngMaker.createDrawerWindow();

        //Sample
        List<String> sampleLabels = Arrays.asList(new String[] {"sample"});
        String samplePath = pngMaker.createAndSavePNG(mSticks.getSample(),stimObjIds.getSample(), sampleLabels, generatorPngPath);
        experimentPngPaths.setSample(generator.convertPathToExperiment(samplePath));

        //Match
        List<String> matchLabels = Arrays.asList(new String[] {"match"});
        String matchPath = pngMaker.createAndSavePNG(mSticks.getMatch(),stimObjIds.getMatch(), matchLabels, generatorPngPath);
        experimentPngPaths.setMatch(generator.convertPathToExperiment(matchPath));

        //Procedural Distractors
        List<String> proceduralDistractorLabels = Arrays.asList(new String[] {"procedural"});
        for (int i = 0; i < numProceduralDistractors; i++) {
            String proceduralDistractorPath = pngMaker.createAndSavePNG(mSticks.proceduralDistractors.get(i),stimObjIds.proceduralDistractors.get(i), proceduralDistractorLabels, generatorPngPath);
            experimentPngPaths.addProceduralDistractor(generator.convertPathToExperiment(proceduralDistractorPath));
        }

        //Rand Distractor
        List<String> randDistractorLabels = Arrays.asList(new String[] {"rand"});
        for (int i = 0; i < numRandDistractors; i++) {
            String randDistractorPath = pngMaker.createAndSavePNG(mSticks.randDistractors.get(i),stimObjIds.randDistractors.get(i), randDistractorLabels, generatorPngPath);
            experimentPngPaths.addRandDistractor(generator.convertPathToExperiment(randDistractorPath));
        }

        pngMaker.close();
    }

    private void generateNoiseMap() {
        List<String> noiseMapLabels = new LinkedList<>();
        noiseMapLabels.add("sample");
        generator.getPngMaker().createDrawerWindow();
        String generatorNoiseMapPath = generator.getPngMaker().createAndSaveGaussNoiseMap(mSticks.getSample(), stimObjIds.getSample(), noiseMapLabels, generator.getGeneratorPngPath());
        experimentNoiseMapPath = generator.convertPathToExperiment(generatorNoiseMapPath);
    }

    private void assignCoords() {

        class ProceduralCoordinateAssigner extends NAFCCoordinateAssigner{

            private final int numProceduralDistractors;
            private final int numRandDistractors;
            private Procedural<Coordinates2D> coords;

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

    private void writeStimObjDataSpecs() {
        //Sample
        double xCenter = coords.getSample().getX();
        double yCenter = coords.getSample().getY();
        double imageSize = parameters.getSize();
        ImageDimensions dimensions = new ImageDimensions(imageSize, imageSize);
        String path = experimentPngPaths.getSample();
        String noiseMapPath = experimentNoiseMapPath;
        Color color = parameters.color;
        NoisyPngSpec sampleSpec = new NoisyPngSpec(
                xCenter, yCenter,
                dimensions,
                path,
                noiseMapPath,
                color);
        MStickStimObjData sampleMStickObjData = new MStickStimObjData("sample", mStickSpecs.getSample());
        generator.getDbUtil().writeStimObjData(stimObjIds.getSample(), sampleSpec.toXml(), sampleMStickObjData.toXml());

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
        generator.getDbUtil().writeStimObjData(stimObjIds.getMatch(), matchSpec.toXml(), matchMStickObjData.toXml());

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
            generator.getDbUtil().writeStimObjData(stimObjIds.proceduralDistractors.get(i), proceduralDistractorSpec.toXml(), proceduralDistractorMStickObjData.toXml());
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
            generator.getDbUtil().writeStimObjData(stimObjIds.randDistractors.get(i), randDistractorSpec.toXml(), randDistractorMStickObjData.toXml());
        }
    }

    private void assignTaskId() {
        setTaskId(stimObjIds.getSample());
    }

    private void writeStimSpec(){
        NAFCStimSpecWriter stimSpecWriter = new NAFCStimSpecWriter(
                getStimId(),
                generator.getDbUtil(),
                parameters,
                coords,
                parameters.numChoices,
                stimObjIds);

        stimSpecWriter.writeStimSpec();
    }

    private void setTaskId(Long sample) {
        this.taskId = sample;
    }

    @Override
    public Long getStimId() {
        return taskId;
    }
    public static class ProceduralStimParameters extends NAFCTrialParameters{

        double noiseChance;
        int numChoices;
        int numRandDistractors;
        double morphMagnitude;
        Color color;
    }
}