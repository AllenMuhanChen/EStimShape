package org.xper.intan;

import org.xper.Dependency;

/**
 * Provides experiment-relevant control of Intan for stimulation and recording
 */
public class IntanStimulationController extends IntanRecordingController{



    @Dependency
    IntanClient intanClient;



    public void setStimParameter(){

    }

    public void trigger(){

    }

    public static String tcpNameForIntanChannel(RHSChannel channel){
        // turn ENUM into string all lower case, with hypen between channel
        // letter and numbers
        String channelName = channel.toString().toLowerCase();
        channelName = channelName.replaceAll("([a-z])([0-9])", "$1-$2");
        return channelName;
    }


}