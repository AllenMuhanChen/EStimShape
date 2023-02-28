package org.xper.allen.ga3d.blockgen;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.RandMStickGenerator;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;
import org.xper.utils.RGBColor;

import java.util.LinkedList;
import java.util.List;

public class RandStim extends ThreeDGAStim {

    public RandStim(GA3DBlockGenerator generator, double size, Coordinates2D coords) {
        super(generator, size, coords);
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        //Assign StimSpecId
        stimId = generator.getGlobalTimeUtil().currentTimeMicros();

        RandMStickGenerator mStickGenerator = new RandMStickGenerator(generator.getMaxImageDimensionDegrees());
        AllenMatchStick mStick = mStickGenerator.getMStick();
        mStickGenerator.getMStickSpec().writeInfo2File(generator.getGeneratorSpecPath() + "/" + Long.toString(stimId), true);

        //shading
        mStick.setTextureType("SHADE");
        //color
        mStick.setStimColor(new RGBColor(1,1,1));

        //png
        //draw pngs
        List<String> labels = new LinkedList<>();
        labels.add(generator.getGaBaseName());
        String pngPath = generator.getPngMaker().createAndSavePNG(mStick, stimId, labels, generator.getGeneratorPngPath());
        pngPath = generator.convertPathToExperiment(pngPath);

        //Create StimSpec
        stimSpec = new PngSpec();
        stimSpec.setPath(pngPath);
        stimSpec.setDimensions(new ImageDimensions(size, size));
        stimSpec.setxCenter(coords.getX());
        stimSpec.setyCenter(coords.getY());

        mStickData = mStickGenerator.getMStick().getMStickData();
        writeStimSpec(stimId);

        System.err.println("Finished Writing Rand Trial");
    }


    @Override
    public Long getStimId() {
        return stimId;
    }
}
