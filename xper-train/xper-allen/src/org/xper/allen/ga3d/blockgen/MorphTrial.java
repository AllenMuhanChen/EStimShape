package org.xper.allen.ga3d.blockgen;

import org.xper.allen.Trial;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.ga.drawing.GAMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.stick.MStickSpec;
import org.xper.drawing.stick.MatchStick;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;

import java.util.Map;

public class MorphTrial extends ThreeDGATrial {

    private Long parentId;
    private long taskId;

    public MorphTrial(GA3DBlockGen generator, Long parentId) {
        super(generator);
        this.parentId = parentId;
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void write() {
        //asign stimId
        long id = generator.getGlobalTimeUtil().currentTimeMicros();

        //generate Match Sticks
        AllenMatchStick mStick = new AllenMatchStick();
        mStick.setProperties(generator.getMaxImageDimensionDegrees());
        mStick.genMatchStickFromShapeSpec(AllenMStickSpec.fromXml(getMStickSpec(parentId)),new double[]{0,0,0});
        mStick.mutate(0);


        //draw pngs
        String pngPath = generator.getPngMaker().createAndSavePNG(mStick, id, generator.getGeneratorPngPath());
        pngPath = generator.convertPathToExperiment(pngPath);

        Coordinates2D coords = getCoordsFromParent();
        double size = getSizeFromParent();

        //write spec
        taskId = id;

        PngSpec spec = new PngSpec();
        spec.setPath(pngPath);
        spec.setDimensions(new ImageDimensions(size,size));

        AllenMStickSpec mStickSpec = new AllenMStickSpec();
        mStickSpec.setMStickInfo(mStick);
        generator.getDbUtil().writeStimSpec(taskId, spec.toXml(), mStickSpec.toXml());

        System.err.println("Finished Writing Morph Trial");
    }

    private String getMStickSpec(Long parentId) {
        return generator.getDbUtil().readStimSpecDataByIdRangeAsMap(parentId, parentId).get(parentId);
    }

    @Override
    public Long getTaskId() {
        return taskId;
    }


    public Coordinates2D getCoordsFromParent(){ //TODO
        return new Coordinates2D();
    }

    public double getSizeFromParent(){ //TODO
        return 0;
    }
}
