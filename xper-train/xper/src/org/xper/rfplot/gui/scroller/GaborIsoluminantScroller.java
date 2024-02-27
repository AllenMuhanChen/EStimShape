package org.xper.rfplot.gui.scroller;

import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.gabor.IsoluminantGaborSpec;

public class GaborIsoluminantScroller <T extends IsoluminantGaborSpec> extends RFPlotScroller<T>{
    public GaborIsoluminantScroller(Class<T> type) {
        this.type = type;
    }

    RGBColor[][] colors = {
        new RGBColor[]{
                new RGBColor(0.5f, 0.5f, 0),
                new RGBColor(0, 0.5f, 0.5f)},
        new RGBColor[]{
                new RGBColor(1f, 0, 0f),
                new RGBColor(0f, 1f, 0)}
        };

    boolean[] modRedGreen = {true, true};
    boolean[] modBlueYellow = {true, true};



    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        T currentGaborSpec = getCurrentSpec(scrollerParams, type);
        RGBColor color1 = currentGaborSpec.getColor1();
        RGBColor color2 = currentGaborSpec.getColor2();
        boolean modRedGreen = currentGaborSpec.isModRedGreen();
        boolean modBlueYellow = currentGaborSpec.isModBlueYellow();

        int index;
        if (color1.equals(colors[0][0])
                && color2.equals(colors[0][1])
                && modRedGreen == this.modRedGreen[0]
                && modBlueYellow == this.modBlueYellow[0]) {
            index = 0;
            System.out.println("recognized index 0");
        }
        else if (color1.equals(colors[1][0])
                && color2.equals(colors[1][1])
                && modRedGreen == this.modRedGreen[1]
                && !modBlueYellow == this.modBlueYellow[1]) {
            index = 1;
            System.out.println("recognized index 1");
        }
        else{
            index = -1;
        }

        RGBColor newColor1 = colors[(index + 1) % colors.length][0];
        RGBColor newColor2 = colors[(index + 1) % colors.length][1];
        boolean newModRedGreen = this.modRedGreen[index+1];
        boolean newModBlueYellow = this.modBlueYellow[index+1];

        setNewParams(scrollerParams, newColor1, newColor2, newModRedGreen, newModBlueYellow);
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        T currentGaborSpec = getCurrentSpec(scrollerParams, type);
        RGBColor color1 = currentGaborSpec.getColor1();
        RGBColor color2 = currentGaborSpec.getColor2();
        boolean modRedGreen = currentGaborSpec.isModRedGreen();
        boolean modBlueYellow = currentGaborSpec.isModBlueYellow();

        int index;
        if (color1.equals(colors[0][0])
                && color2.equals(colors[0][1])
                && modRedGreen == this.modRedGreen[0]
                && modBlueYellow == this.modBlueYellow[0]) {
            index = 0;
            System.out.println("recognized index 0");
        }
        else if (color1.equals(colors[1][0])
                && color2.equals(colors[1][1])
                && modRedGreen == this.modRedGreen[1]
                && !modBlueYellow == this.modBlueYellow[1]) {
            index = 1;
            System.out.println("recognized index 1");
        }
        else{
            index = 1;

        }

        RGBColor newColor1 = colors[(index - 1 + colors.length) % colors.length][0];
        RGBColor newColor2 = colors[(index - 1 + colors.length) % colors.length][1];
        boolean newModRedGreen = this.modRedGreen[(index - 1 + colors.length) % colors.length];
        boolean newModBlueYellow = this.modBlueYellow[(index - 1 + colors.length) % colors.length];

        setNewParams(scrollerParams, newColor1, newColor2, newModRedGreen, newModBlueYellow);
        return scrollerParams;
    }



    private void setNewParams(ScrollerParams scrollerParams, RGBColor newColor1, RGBColor newColor2, boolean newModRedGreen, boolean newModBlueYellow) {
        T currentGaborSpec = getCurrentSpec(scrollerParams, type);
        currentGaborSpec.setColor1(newColor1);
        currentGaborSpec.setColor2(newColor2);
        currentGaborSpec.setModRedGreen(newModRedGreen);
        currentGaborSpec.setModBlueYellow(newModBlueYellow);
        scrollerParams.getRfPlotDrawable().setSpec(currentGaborSpec.toXml());
    }
}