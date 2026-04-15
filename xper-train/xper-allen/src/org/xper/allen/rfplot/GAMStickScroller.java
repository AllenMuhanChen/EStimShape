package org.xper.allen.rfplot;

import org.xper.Dependency;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.rfplot.RFPlotMatchStick.RFPlotMatchStickSpec;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.List;

/**
 * RFPlot scroller that cycles through GA stims sorted by response (highest to lowest).
 * Stim IDs are read from the StimGaInfo table via dbUtil, and the corresponding
 * shape spec is loaded from gaSpecPath/<stimId>_spec.xml.
 */
public class GAMStickScroller extends RFPlotScroller<RFPlotMatchStickSpec> {
    @Dependency
    private String gaSpecPath;

    @Dependency
    private MultiGaDbUtil dbUtil;

    private List<Long> sortedStimIds;
    private int currentIndex = -1;

    public GAMStickScroller() {
        this.type = RFPlotMatchStickSpec.class;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        initStimIds();
        if (sortedStimIds.isEmpty()) {
            return scrollerParams;
        }
        currentIndex = (currentIndex + 1) % sortedStimIds.size();
        return loadCurrentStim(scrollerParams);
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        initStimIds();
        if (sortedStimIds.isEmpty()) {
            return scrollerParams;
        }
        if (currentIndex <= 0) {
            currentIndex = sortedStimIds.size() - 1;
        } else {
            currentIndex--;
        }
        return loadCurrentStim(scrollerParams);
    }

    private void initStimIds() {
        if (sortedStimIds == null) {
            sortedStimIds = dbUtil.readAllStimIdsSortedByResponse();
            currentIndex = -1;
        }
    }

    private ScrollerParams loadCurrentStim(ScrollerParams scrollerParams) {
        long stimId = sortedStimIds.get(currentIndex);
        AllenMStickSpec loadedSpec = readSpecFromFile(stimId);

        RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStickSpec newSpec = new RFPlotMatchStickSpec(currentSpec);
        newSpec.setSpec(loadedSpec);

        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        scrollerParams.setNewValue("GA Stim: " + stimId + " (" + (currentIndex + 1) + "/" + sortedStimIds.size() + ")");
        return scrollerParams;
    }

    private AllenMStickSpec readSpecFromFile(long stimId) {
        String fname = gaSpecPath + "/" + stimId + "_spec.xml";
        StringBuilder fileData = new StringBuilder();
        try {
            BufferedReader reader = new BufferedReader(new FileReader(fname));
            char[] buf = new char[1024];
            int numRead;
            while ((numRead = reader.read(buf)) != -1) {
                fileData.append(buf, 0, numRead);
            }
            reader.close();
        } catch (Exception e) {
            throw new RuntimeException("Error reading spec file: " + fname, e);
        }
        return AllenMStickSpec.fromXml(fileData.toString());
    }

    public String getGaSpecPath() {
        return gaSpecPath;
    }

    public void setGaSpecPath(String gaSpecPath) {
        this.gaSpecPath = gaSpecPath;
    }

    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }
}
