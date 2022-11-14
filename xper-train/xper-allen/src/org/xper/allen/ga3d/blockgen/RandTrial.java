package org.xper.allen.ga3d.blockgen;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.RandMStickGenerator;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;
import org.xper.utils.RGBColor;

import java.util.Collections;

public class RandTrial extends ThreeDGATrial {

    public RandTrial(GA3DBlockGen generator) {
        super(generator);
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void write() {
        RandMStickGenerator mStickGenerator = new RandMStickGenerator(5);
        AllenMatchStick mStick = mStickGenerator.getMStick();

        //shading
        mStick.setTextureType("SHADE");
        //color
        mStick.setStimColor(new RGBColor(1,1,1));
        //location
        Coordinates2D coords = new Coordinates2D(0,0);
        //size
        double size = 5;

        //Assign StimSpecId
        long id = generator.getGlobalTimeUtil().currentTimeMicros();

        //png
        String pngPath = generator.getPngMaker().createAndSavePNG(mStick, id, Collections.singletonList(""), generator.getGeneratorPngPath());
        pngPath = generator.convertPathToExperiment(pngPath);

        //Create StimSpec
        PngSpec spec = new PngSpec();
        spec.setPath(pngPath);
        spec.setDimensions(new ImageDimensions(size, size));
        spec.setxCenter(coords.getX());
        spec.setyCenter(coords.getY());

        generator.getDbUtil().writeStimSpec(id, spec.toXml(), mStickGenerator.getMStickSpec().toXml());
    }

    @Override
    public Long getTaskId() {
        return null;
    }
}
