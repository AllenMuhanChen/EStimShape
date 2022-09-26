package org.xper.rfplot;

import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.util.ThreadUtil;

import java.util.Random;

public class RFPlotStimTest {

    static String host = "172.30.6.90";
    static RFPlotTaskDataSourceClient client = new RFPlotTaskDataSourceClient("localhost", RFPlotTaskDataSource.DEFAULT_RF_PLOT_TASK_DATA_SOURCE_PORT);

    public static void main(String[] args) {
        streamRandomWalk();
    }

    private static void streamRandomWalk() {
        RFPlotStimSpec stimSpec = new RFPlotStimSpec();
        GaborSpec gaborSpec = new GaborSpec();
        gaborSpec.setPhase(0);
        gaborSpec.setFrequency(1);
        gaborSpec.setOrientation(0);
        gaborSpec.setAnimation(true);
        gaborSpec.setSize(10);
        gaborSpec.setXCenter(0);
        gaborSpec.setYCenter(0);
        stimSpec.setStimSpec(gaborSpec.toXml());
        stimSpec.setStimClass(RFPlotGaborObject.class.getName());

        RFPlotXfmSpec xfmSpec = RFPlotXfmSpec.fromXml(null);
        xfmSpec.setColor(new RGBColor(1.0f,1.0f,1.0f));
        double prevX=0;
        double prevY=0;
        while(true){
            Random r = new Random();
            double stepSize = 10;
            double randX = r.nextDouble()*stepSize-stepSize/2;
            double randY = r.nextDouble()*stepSize-stepSize/2;
            double newX = prevX + randX;
            double newY = prevY + randY;
            xfmSpec.setTranslation(new Coordinates2D(newX, newY));
            prevX = newX;
            prevY = newY;

            client.changeRFPlotStim(stimSpec.toXml());
            client.changeRFPlotXfm(xfmSpec.toXml());

            ThreadUtil.sleep(16);
        }
    }
}
