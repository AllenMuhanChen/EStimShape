package org.xper.allen.fixation.blockgen;

import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.experiment.ExperimentMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.blockgen.NAFCCoordinateAssigner;

import org.xper.allen.specs.NoisyPngSpec;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;

import java.util.Collections;

public class NoisyPngFixationStim implements Stim {

    private long id;

    private final NoisyPngFixationBlockGen generator;
    private final NoisyPngFixationTrialParameters params;

    public NoisyPngFixationStim(NoisyPngFixationBlockGen generator, NoisyPngFixationTrialParameters params) {
        this.generator = generator;
        this.params = params;
    }

    @Override
    public void preWrite() {}


    @Override
    public void writeStim() {
        //Generate MStick
        ProceduralMatchStick mStick = new ProceduralMatchStick();
        mStick.setProperties(generator.getMaxImageDimensionDegrees(), "SHADE");
        mStick.setStimColor(params.color);
        mStick.genMatchStickRand();


        //Assign StimSpecId
        id = generator.getGlobalTimeUtil().currentTimeMicros();

        //Create Png
        String pngPath = generator.getPngMaker().createAndSavePNG(mStick, id, Collections.singletonList(""), generator.getGeneratorPngPath());
        pngPath = generator.convertPngPathToExperiment(pngPath);

        //Create NoiseMap
        int noiseCompIndx = mStick.chooseRandLeaf();
        String noiseMapPath = generator.getPngMaker().createAndSaveGaussNoiseMap((ExperimentMatchStick) mStick, id, Collections.singletonList(""), generator.getGeneratorPngPath(), params.noiseChance, noiseCompIndx);
        noiseMapPath = generator.convertPngPathToExperiment(noiseMapPath);

        //Assign Coordinates
        Coordinates2D coords = NAFCCoordinateAssigner.randomCoordsWithinRadii(params.distanceLims.getLowerLim(), params.distanceLims.getUpperLim());

        //Create StimSpec
        NoisyPngSpec spec = new NoisyPngSpec();
        spec.setPngPath(pngPath);
        spec.setNoiseMapPath(noiseMapPath);
        spec.setDimensions(new ImageDimensions(params.getSize(), params.getSize()));
        spec.setxCenter(coords.getX());
        spec.setyCenter(coords.getY());

        //Write Spec
        generator.getDbUtil().writeStimSpec(id, spec.toXml());
    }


    @Override
    public Long getTaskId() {
        return id;
    }
}