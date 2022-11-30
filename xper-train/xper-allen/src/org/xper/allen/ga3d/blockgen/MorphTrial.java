package org.xper.allen.ga3d.blockgen;

import org.xper.allen.Trial;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.ga.drawing.GAMatchStick;
import org.xper.db.vo.StimSpecEntry;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.stick.MStickSpec;
import org.xper.drawing.stick.MatchStick;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;

import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;

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
        List<String> labels = new LinkedList<>();
        labels.add(generator.getGaName());
        labels.add(Long.toString(parentId));
        String pngPath = generator.getPngMaker().createAndSavePNG(mStick, id, labels, generator.getGeneratorPngPath());
        pngPath = generator.convertPathToExperiment(pngPath);

        Coordinates2D parentCoords = getCoordsFromParent();
        double parentSize = getSizeFromParent();

        Coordinates2D coords = morphCoords(parentCoords, parentSize);
        double size = morphSize(parentSize);

        //write spec
        taskId = id;

        PngSpec spec = new PngSpec();
        spec.setPath(pngPath);
        spec.setDimensions(new ImageDimensions(size,size));
        spec.setxCenter(coords.getX());
        spec.setyCenter(coords.getY());

        AllenMStickSpec mStickSpec = new AllenMStickSpec();
        mStickSpec.setMStickInfo(mStick);
        generator.getDbUtil().writeStimSpec(taskId, spec.toXml(), mStickSpec.toXml());

        System.err.println("Finished Writing Morph Trial");
    }

    private double morphSize(double parentSize) {
        double scalar = truncatedNormal(0.6, 1.4);
        return parentSize * scalar;
    }

    private double truncatedNormal(double lowerBound, double upperBound){
        Random r = new Random();
        double output = r.nextGaussian();
        while(output<lowerBound && output>upperBound){
            output = r.nextGaussian();
        }
        return output;
    }

    private Coordinates2D morphCoords(Coordinates2D parentCoords, double parentSize) {
        double dr = parentSize /2;
        double dtheta = ThreadLocalRandom.current().nextDouble() * 2 * Math.PI;
        Coordinates2D coordShift = polarToCart(dr, dtheta);
        return new Coordinates2D(parentCoords.getX() + coordShift.getX(), parentCoords.getY() + coordShift.getY());
    }

    private String getMStickSpec(Long parentId) {
        return generator.getDbUtil().readStimSpecDataByIdRangeAsMap(parentId, parentId).get(parentId);
    }

    @Override
    public Long getTaskId() {
        return taskId;
    }


    public Coordinates2D getCoordsFromParent(){ //TODO
        PngSpec parentStimSpec = getParentPngSpec();
        return new Coordinates2D(parentStimSpec.getxCenter(), parentStimSpec.getyCenter());
    }

    private PngSpec getParentPngSpec() {
        StimSpecEntry sse  = generator.getDbUtil().readStimSpec(parentId);
        return PngSpec.fromXml(sse.getSpec());
    }

    public double getSizeFromParent(){ //TODO
        PngSpec parentStimSpec = getParentPngSpec();
        return parentStimSpec.getDimensions().getHeight();
    }

    protected static Coordinates2D polarToCart(double r, double theta){
        Coordinates2D output = new Coordinates2D();
        double x = 0 + r * Math.cos(theta);
        double y = 0 + r * Math.sin(theta);
        output.setX(x);
        output.setY(y);
        return output;
    }

}
