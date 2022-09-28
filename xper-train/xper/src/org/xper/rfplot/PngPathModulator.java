package org.xper.rfplot;

import org.xper.rfplot.drawing.RFPlotDrawable;
import org.xper.rfplot.drawing.RFPlotPngObject;
import org.xper.rfplot.drawing.png.PngSpec;
import org.xper.rfplot.gui.CyclicIterator;

import java.io.File;
import java.io.FileFilter;
import java.util.Arrays;

public class PngPathModulator implements RFPlotModulator{

    String libraryPath;
    CyclicIterator<File> pngs;


    public PngPathModulator(String libraryPath) {
        this.libraryPath = libraryPath;

        File path = new File(libraryPath);
        pngs = new CyclicIterator<>(Arrays.asList(path.listFiles(new FileFilter() {
            @Override
            public boolean accept(File pathname) {
                return pathname.getAbsolutePath().contains(".png");
            }
        })));

    }

    @Override
    public RFPlotStimSpec next(RFPlotStimSpec current) {
        String nextPath = pngs.next().getAbsolutePath();

        PngSpec pngSpec = PngSpec.fromXml(current.getStimSpec());
        pngSpec.setPath(nextPath);

        current.setStimSpec(pngSpec.toXml());
        return current;
    }

    @Override
    public RFPlotStimSpec previous(RFPlotStimSpec current) {
        String nextPath = pngs.previous().getAbsolutePath();

        PngSpec pngSpec = PngSpec.fromXml(current.getStimSpec());
        pngSpec.setPath(nextPath);

        current.setStimSpec(pngSpec.toXml());
        return current;
    }

    @Override
    public void nextMode() {

    }

    @Override
    public void previousMode() {

    }

}
