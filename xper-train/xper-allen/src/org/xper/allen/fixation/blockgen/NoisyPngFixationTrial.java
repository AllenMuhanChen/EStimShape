package org.xper.allen.fixation.blockgen;

import org.xper.allen.Trial;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.RandMStickGenerator;
import org.xper.allen.nafc.blockgen.NAFCCoordinateAssigner;

import org.xper.allen.specs.NoisyPngSpec;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;

import java.util.Collections;

public class NoisyPngFixationTrial implements Trial {

    private long id;

    private final NoisyPngFixationBlockGen generator;
    private final NoisyPngFixationTrialParameters params;

    public NoisyPngFixationTrial(NoisyPngFixationBlockGen generator, NoisyPngFixationTrialParameters params) {
        this.generator = generator;
        this.params = params;
    }

    @Override
    public void preWrite() {}


    @Override
    public void writeStimSpec() {
        //Generate MStick
        RandMStickGenerator mStickGenerator = new RandMStickGenerator(generator.getMaxImageDimensionDegrees());
        AllenMatchStick mStick = mStickGenerator.getMStick();

        //Assign StimSpecId
        id = generator.getGlobalTimeUtil().currentTimeMicros();

        //Create Png
        String pngPath = generator.getPngMaker().createAndSavePNG(mStick, id, Collections.singletonList(""), generator.getGeneratorPngPath());
        pngPath = generator.convertPathToExperiment(pngPath);

        //Create NoiseMap
        mStick.setNoiseParameters(params.getNoiseParameters());
        String noiseMapPath = generator.getPngMaker().createAndSaveNoiseMap(mStick, id, Collections.singletonList(""), generator.getGeneratorPngPath());
        noiseMapPath = generator.convertPathToExperiment(noiseMapPath);

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
        generator.getDbUtil().writeStimSpec(id, spec.toXml(), "");
    }


    @Override
    public Long getStimId() {
        return id;
    }
}
