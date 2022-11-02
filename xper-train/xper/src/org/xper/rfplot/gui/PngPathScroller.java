package org.xper.rfplot.gui;

import org.xper.rfplot.drawing.png.PngSpec;

import java.io.File;
import java.io.FileFilter;
import java.util.Arrays;

public class PngPathScroller extends RFPlotScroller {

    String libraryPath_generator;
    String libraryPath_experiment;
    CyclicIterator<File> pngs;

    public PngPathScroller(String libraryPath_generator, String libraryPath_experiment) {
        this.libraryPath_generator = libraryPath_generator;
        this.libraryPath_experiment = libraryPath_experiment;

        setPngsFromLibrary(libraryPath_generator);
    }

    private void setPngsFromLibrary(String libraryPath) {
        File path = new File(libraryPath);
        pngs = new CyclicIterator<>(Arrays.asList(path.listFiles(new FileFilter() {
            @Override
            public boolean accept(File pathname) {
                return pathname.getAbsolutePath().contains(".png");
            }
        })));
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        String nextPath = pngs.next().getAbsolutePath();
        nextPath = convertGeneratorToExperiment(nextPath);
        PngSpec pngSpec = PngSpec.fromXml(scrollerParams.getRfPlotDrawable().getSpec());
        pngSpec.setPath(nextPath);
        scrollerParams.getRfPlotDrawable().setSpec(pngSpec.toXml());
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        String nextPath = pngs.previous().getAbsolutePath();
        nextPath = convertGeneratorToExperiment(nextPath);
        PngSpec pngSpec = PngSpec.fromXml(scrollerParams.getRfPlotDrawable().getSpec());
        pngSpec.setPath(nextPath);
        scrollerParams.getRfPlotDrawable().setSpec(pngSpec.toXml());
        return scrollerParams;
    }

    private String convertGeneratorToExperiment(String imagePath){
        String newPath = imagePath.replace(libraryPath_generator, libraryPath_experiment);
        return newPath;
    }
}
