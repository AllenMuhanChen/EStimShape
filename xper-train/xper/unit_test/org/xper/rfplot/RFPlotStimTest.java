package org.xper.rfplot;

import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.util.ThreadUtil;

import java.util.Random;

public class RFPlotStimTest {

    static String host = "172.30.6.90";
    static RFPlotTaskDataSourceClient client = new RFPlotTaskDataSourceClient("localhost", RFPlotTaskDataSource.DEFAULT_RF_PLOT_TASK_DATA_SOURCE_PORT);

    public static void main(String[] args) {
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
        while(true){
            Random r = new Random();
            double randX = r.nextDouble()*20-10;
            double randY = r.nextDouble()*20-10;
            xfmSpec.setTranslation(new Coordinates2D(randX, randY));

            client.changeRFPlotStim(stimSpec.toXml());

            ThreadUtil.sleep(100);

            client.changeRFPlotXfm(xfmSpec.toXml());

            ThreadUtil.sleep(100);
        }
    }
}
