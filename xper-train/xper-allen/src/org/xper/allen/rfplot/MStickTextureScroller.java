package org.xper.allen.rfplot;

import org.xper.rfplot.gui.CyclicIterator;
import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;

import java.util.Arrays;
import java.util.List;

public class MStickTextureScroller<T extends RFPlotMatchStick.RFPlotMatchStickSpec> extends RFPlotScroller<T> {
    private List<String> textures = Arrays.asList("SHADE", "SPECULAR", "2D");
    public MStickTextureScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotMatchStick.RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStick.RFPlotMatchStickSpec newSpec = new RFPlotMatchStick.RFPlotMatchStickSpec(currentSpec);
        String currentTexture = currentSpec.getTexture();
        CyclicIterator<String> cyclicIterator = new CyclicIterator<>(textures);

        //GO to the current texture
        while (cyclicIterator.hasNext()) {
            if (cyclicIterator.next().equals(currentTexture)) {
                break;
            }
        }
        newSpec.setTexture(cyclicIterator.next());

        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        scrollerParams.setNewValue("Matchstick Texture: " + newSpec.getTexture());
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RFPlotMatchStick.RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStick.RFPlotMatchStickSpec newSpec = new RFPlotMatchStick.RFPlotMatchStickSpec(currentSpec);
        String currentTexture = currentSpec.getTexture();
        CyclicIterator<String> cyclicIterator = new CyclicIterator<>(textures);

        //GO to the current texture
        while (cyclicIterator.hasNext()) {
            if (cyclicIterator.next().equals(currentTexture)) {
                break;
            }
        }
        newSpec.setTexture(cyclicIterator.previous());

        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        scrollerParams.setNewValue("Matchstick Texture: " + newSpec.getTexture());
        return scrollerParams;
    }
}