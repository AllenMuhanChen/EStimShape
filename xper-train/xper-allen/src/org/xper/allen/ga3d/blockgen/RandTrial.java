package org.xper.allen.ga3d.blockgen;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.RandMStickGenerator;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;
import org.xper.utils.RGBColor;

import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

public class RandTrial extends ThreeDGATrial {

    private double size;
    private Coordinates2D coords;
    private long id;

    public RandTrial(GA3DBlockGen generator, double size, Coordinates2D coords) {
        super(generator);
        this.size = size;
        this.coords = coords;
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void write() {
        //Assign StimSpecId
        id = generator.getGlobalTimeUtil().currentTimeMicros();

        RandMStickGenerator mStickGenerator = new RandMStickGenerator(generator.getMaxImageDimensionDegrees());
        AllenMatchStick mStick = mStickGenerator.getMStick();
        mStickGenerator.getMStickSpec().writeInfo2File(generator.getGeneratorSpecPath() + "/" + Long.toString(id), true);

        //shading
        mStick.setTextureType("SHADE");
        //color
        mStick.setStimColor(new RGBColor(1,1,1));

        //png
        //draw pngs
        List<String> labels = new LinkedList<>();
        labels.add(generator.getGaName());
        String pngPath = generator.getPngMaker().createAndSavePNG(mStick, id, labels, generator.getGeneratorPngPath());
        pngPath = generator.convertPathToExperiment(pngPath);

        //Create StimSpec
        PngSpec spec = new PngSpec();
        spec.setPath(pngPath);
        spec.setDimensions(new ImageDimensions(size, size));
        spec.setxCenter(coords.getX());
        spec.setyCenter(coords.getY());

        AllenMStickData mStickData = mStickGenerator.getMStick().getMStickData();
        generator.getDbUtil().writeStimSpec(id, spec.toXml(), mStickData.toXml());

        System.err.println("Finished Writing Rand Trial");
    }

    @Override
    public Long getTaskId() {
        return id;
    }
}
