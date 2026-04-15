package org.xper.allen.rfplot;

import org.xper.Dependency;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.rfplot.RFPlotMatchStick.RFPlotMatchStickSpec;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * RFPlot scroller that cycles through the top N GA stims per probe channel,
 * ordered top-to-bottom along the probe (DBCChannelMapper order).
 *
 * Scroll sequence: ch7 rank1, ch7 rank2, ..., ch8 rank1, ch8 rank2, ...
 *
 * Responses are averaged across reps from the ChannelResponses table.
 * Shape specs are loaded from gaSpecPath/<stimId>_spec.xml.
 */
public class ChannelMStickScroller extends RFPlotScroller<RFPlotMatchStickSpec> {

    /** Probe channels ordered top → bottom (DBCChannelMapper order). */
    static final int[] CHANNEL_ORDER = {
             7,  8, 25, 22,  0, 15, 24, 23,
             6,  9, 26, 21,  5, 10, 31, 16,
            27, 20,  4, 11, 28, 19,  1, 14,
             3, 12, 29, 18,  2, 13, 30, 17
    };
    @Dependency
    private String gaSpecPath;
    @Dependency
    private MultiGaDbUtil dbUtil;
    @Dependency
    private int topN = 2;

    private List<ChannelStimEntry> scrollSequence;
    private int currentIndex = -1;

    public ChannelMStickScroller() {
        this.type = RFPlotMatchStickSpec.class;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        initScrollSequence();
        System.out.println("Scroll sequence size: " + scrollSequence.size());
        if (scrollSequence.isEmpty()) {
            return scrollerParams;
        }
        currentIndex = (currentIndex + 1) % scrollSequence.size();
        return loadCurrentStim(scrollerParams);
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        initScrollSequence();
        if (scrollSequence.isEmpty()) {
            return scrollerParams;
        }
        if (currentIndex <= 0) {
            currentIndex = scrollSequence.size() - 1;
        } else {
            currentIndex--;
        }
        return loadCurrentStim(scrollerParams);
    }

    /** Maps an integer channel number to its DB key format, e.g. 30 → "A-030". */
    static String toDbChannelKey(int channel) {
        return String.format("A-%03d", channel);
    }

    private void initScrollSequence() {
        if (scrollSequence != null) {
            return;
        }
        Map<String, List<Long>> topStimIdsPerChannel = dbUtil.readTopNStimIdsPerChannel(topN);

        scrollSequence = new ArrayList<>();
        for (int channel : CHANNEL_ORDER) {
            String dbKey = toDbChannelKey(channel);
            List<Long> topStims = topStimIdsPerChannel.getOrDefault(dbKey, Collections.emptyList());
            for (int rank = 0; rank < topStims.size(); rank++) {
                long stimId = topStims.get(rank);
                String label = "Ch " + channel + " #" + (rank + 1) + "/" + topStims.size() + " [" + stimId + "]";
                System.out.println("Adding to scroll sequence: " + label);
                scrollSequence.add(new ChannelStimEntry(stimId, label));
            }
        }
        currentIndex = -1;
    }

    private ScrollerParams loadCurrentStim(ScrollerParams scrollerParams) {
        ChannelStimEntry entry = scrollSequence.get(currentIndex);
        AllenMStickSpec loadedSpec = readSpecFromFile(entry.stimId);

        RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStickSpec newSpec = new RFPlotMatchStickSpec(currentSpec);
        newSpec.setSpec(loadedSpec);

        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        scrollerParams.setNewValue(entry.label);
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

    public int getTopN() {
        return topN;
    }

    public void setTopN(int topN) {
        this.topN = topN;
    }

    private static class ChannelStimEntry {
        final long stimId;
        final String label;

        ChannelStimEntry(long stimId, String label) {
            this.stimId = stimId;
            this.label = label;
        }
    }
}
