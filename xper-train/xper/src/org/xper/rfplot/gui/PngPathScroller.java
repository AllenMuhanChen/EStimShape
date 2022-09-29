package org.xper.rfplot.gui;

import org.xper.rfplot.RFPlotClient;
import org.xper.rfplot.RFPlotStimSpec;
import org.xper.rfplot.drawing.RFPlotDrawable;
import org.xper.rfplot.drawing.png.PngSpec;

import java.io.File;
import java.io.FileFilter;
import java.util.Arrays;

public class PngPathScroller extends RFPlotScroller {

    String libraryPath;
    CyclicIterator<File> pngs;

    public PngPathScroller(RFPlotClient client, String libraryPath) {
        super(client);
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
    public void next(RFPlotDrawable pngDrawable) {
        String nextPath = pngs.next().getAbsolutePath();
        PngSpec pngSpec = PngSpec.fromXml(pngDrawable.getSpec());
        pngSpec.setPath(nextPath);
        pngDrawable.setSpec(pngSpec.toXml());
        String newStimSpec = RFPlotStimSpec.getStimSpecFromRFPlotDrawable(pngDrawable);
        client.changeRFPlotStim(newStimSpec);
    }

    @Override
    public void previous(RFPlotDrawable pngDrawable) {
        String nextPath = pngs.previous().getAbsolutePath();
        PngSpec pngSpec = PngSpec.fromXml(pngDrawable.getSpec());
        pngSpec.setPath(nextPath);
        pngDrawable.setSpec(pngSpec.toXml());
        String newStimSpec = RFPlotStimSpec.getStimSpecFromRFPlotDrawable(pngDrawable);
        client.changeRFPlotStim(newStimSpec);
    }
}
