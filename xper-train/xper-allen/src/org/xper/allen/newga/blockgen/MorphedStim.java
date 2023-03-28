package org.xper.allen.newga.blockgen;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.ga3d.blockgen.GABlockGenerator;
import org.xper.allen.ga3d.blockgen.ThreeDGAStim;
import org.xper.db.vo.StimSpecEntry;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;

import java.util.LinkedList;
import java.util.List;
import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;

public abstract class MorphedStim extends ThreeDGAStim {
    private PngSpec spec;
    private AllenMStickData mStickData;
    private Coordinates2D coords;
    private double size;

    public MorphedStim(GABlockGenerator generator, Long parentId) {
        super(generator, parentId);
    }

    protected static Coordinates2D polarToCart(double r, double theta) {
        Coordinates2D output = new Coordinates2D();
        double x = 0 + r * Math.cos(theta);
        double y = 0 + r * Math.sin(theta);
        output.setX(x);
        output.setY(y);
        return output;
    }

    @Override
    public void writeStim() {
        stimId = generator.getGlobalTimeUtil().currentTimeMicros();

        MorphedMatchStick mStick = morphStim();

        writeMStickData(mStick);

        String pngPath = drawPngs(mStick);

        morphSizeAndCoords();

        writeSpecs(pngPath);

        System.err.println("Finished Writing Morph Trial");
    }

    private void writeSpecs(String pngPath) {
        spec = new PngSpec();
        spec.setPath(pngPath);
        spec.setDimensions(new ImageDimensions(size, size));
        spec.setxCenter(coords.getX());
        spec.setyCenter(coords.getY());

        writeStimSpec(stimId);
    }

    private void morphSizeAndCoords() {
        Coordinates2D parentCoords = getCoordsFromParent();
        double parentSize = getSizeFromParent();
        coords = morphCoords(parentCoords, parentSize);
        size = morphSize(parentSize);
    }

    private String drawPngs(MorphedMatchStick mStick) {
        //draw pngs
        List<String> labels = new LinkedList<>();
        labels.add(generator.getGaBaseName());
        labels.add(Long.toString(parentId));
        String pngPath = generator.getPngMaker().createAndSavePNG(mStick, stimId, labels, generator.getGeneratorPngPath());
        pngPath = generator.convertPathToExperiment(pngPath);
        return pngPath;
    }

    private void writeMStickData(MorphedMatchStick mStick) {
        AllenMStickSpec mStickSpec = new AllenMStickSpec();
        mStickSpec.setMStickInfo(mStick);
        mStickSpec.writeInfo2File(generator.getGeneratorSpecPath() + "/" + Long.toString(stimId), true);
        mStickData = mStick.getMStickData();
    }

    protected abstract MorphedMatchStick morphStim();

    private Coordinates2D morphCoords(Coordinates2D parentCoords, double parentSize) {
        double dr = parentSize / 2;
        double dtheta = ThreadLocalRandom.current().nextDouble() * 2 * Math.PI;
        Coordinates2D coordShift = MorphedStim.polarToCart(dr, dtheta);
        return new Coordinates2D(parentCoords.getX() + coordShift.getX(), parentCoords.getY() + coordShift.getY());
    }

    private double morphSize(double parentSize) {
        double scalar = truncatedNormal(0.6, 1.4);
        return parentSize * scalar;
    }

    private double truncatedNormal(double lowerBound, double upperBound) {
        Random r = new Random();
        double output = r.nextGaussian();
        while (output < lowerBound && output > upperBound) {
            output = r.nextGaussian();
        }
        System.err.println(output);
        return output;
    }

    public Coordinates2D getCoordsFromParent() { //TODO
        PngSpec parentStimSpec = getParentPngSpec();
        return new Coordinates2D(parentStimSpec.getxCenter(), parentStimSpec.getyCenter());
    }

    private PngSpec getParentPngSpec() {
        StimSpecEntry sse = generator.getDbUtil().readStimSpec(parentId);
        return PngSpec.fromXml(sse.getSpec());
    }

    public double getSizeFromParent() { //TODO
        PngSpec parentStimSpec = getParentPngSpec();
        return parentStimSpec.getDimensions().getHeight();
    }

    @Override
    public Long getStimId() {
        return stimId;
    }
}