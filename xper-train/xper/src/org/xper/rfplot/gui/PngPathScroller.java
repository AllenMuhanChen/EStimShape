package org.xper.rfplot.gui;

import org.xper.rfplot.drawing.png.PngSpec;

import java.io.File;
import java.io.FileFilter;
import java.util.Arrays;

public class PngPathScroller extends RFPlotScroller {

    String libraryPath;
    CyclicIterator<File> pngs;

    public PngPathScroller(String libraryPath) {
        this.libraryPath = libraryPath;

        setPngsFromLibrary(libraryPath);
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
        PngSpec pngSpec = PngSpec.fromXml(scrollerParams.getRfPlotDrawable().getSpec());
        pngSpec.setPath(nextPath);
        scrollerParams.getRfPlotDrawable().setSpec(pngSpec.toXml());
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        String nextPath = pngs.previous().getAbsolutePath();
        PngSpec pngSpec = PngSpec.fromXml(scrollerParams.getRfPlotDrawable().getSpec());
        pngSpec.setPath(nextPath);
        scrollerParams.getRfPlotDrawable().setSpec(pngSpec.toXml());
        return scrollerParams;
    }
}
