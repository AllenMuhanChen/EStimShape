package org.xper.allen.ga3d.blockgen;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.db.vo.StimSpecEntry;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;

import java.util.LinkedList;
import java.util.List;
import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;

public class MorphStim extends ThreeDGAStim {

    private String gaName;

    public MorphStim(GA3DLineageBlockGenerator generator, String gaName, Long parentId) {
        super(generator, parentId);
        this.gaName = gaName;
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        //asign stimId
        stimId = generator.getGlobalTimeUtil().currentTimeMicros();

        //generate Match Sticks
        AllenMatchStick mStick = new AllenMatchStick();
        mStick.setProperties(generator.getImageDimensionsDegrees(), "SHADE");

//        mStick.genMatchStickFromShapeSpec(AllenMStickSpec.fromXml(readMStickSpec(parentId)),new double[]{0,0,0});
        boolean mutateSuccess = false;
        while (!mutateSuccess) {
            try {
                mStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");
                mutateSuccess = mStick.mutate(0);

            } catch (Exception e) {
                System.err.println("Mutate failed, retrying...");
                e.printStackTrace();
            }
        }
        AllenMStickSpec mStickSpec = new AllenMStickSpec();
        mStickSpec.setMStickInfo(mStick, true);
        mStickSpec.writeInfo2File(generator.getGeneratorSpecPath() + "/" + Long.toString(stimId), true);
        mStickData = mStick.getMStickData();

        //draw pngs
        List<String> labels = new LinkedList<>();
        labels.add(gaName);
        labels.add(Long.toString(parentId));
        String pngPath = generator.getPngMaker().createAndSavePNG(mStick, stimId, labels, generator.getGeneratorPngPath());
        pngPath = generator.convertPngPathToExperiment(pngPath);

        Coordinates2D parentCoords = getCoordsFromParent();
        double parentSize = getSizeFromParent();

        Coordinates2D coords = morphCoords(parentCoords, parentSize);
        double size = morphSize(parentSize);

        stimSpec = new PngSpec();
        stimSpec.setPath(pngPath);
        stimSpec.setDimensions(new ImageDimensions(size,size));
        stimSpec.setxCenter(coords.getX());
        stimSpec.setyCenter(coords.getY());

        writeStimSpec(stimId);


        System.err.println("Finished Writing Morph Trial");
    }

    public void writeStimSpec(long id) {
        generator.getDbUtil().writeStimSpec(id, stimSpec.toXml(), mStickData.toXml());
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
        System.err.println(output);
        return output;
    }

    private Coordinates2D morphCoords(Coordinates2D parentCoords, double parentSize) {
        double dr = parentSize /2;
        double dtheta = ThreadLocalRandom.current().nextDouble() * 2 * Math.PI;
        Coordinates2D coordShift = polarToCart(dr, dtheta);
        return new Coordinates2D(parentCoords.getX() + coordShift.getX(), parentCoords.getY() + coordShift.getY());
    }

    private String readMStickSpec(Long parentId) {
        return generator.getDbUtil().readStimSpecDataByIdRangeAsMap(parentId, parentId).get(parentId);
    }


    @Override
    public Long getStimId() {
        return stimId;
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