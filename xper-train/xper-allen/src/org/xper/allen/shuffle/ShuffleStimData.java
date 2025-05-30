package org.xper.allen.shuffle;

import org.xper.allen.drawing.composition.*;

import java.util.List;

public class ShuffleStimData extends AllenMStickData {
    ShuffleType shuffleType;


    public ShuffleStimData(AllenMStickData other, ShuffleType shuffleType) {
        super(other);
        this.shuffleType = shuffleType;
    }


    public ShuffleStimData() {
    }

    public String toXml(){
        return ShuffleStimData.toXml(this);
    }

    public static String toXml(ShuffleStimData data){
        return s.toXML(data);
    }

    public static ShuffleStimData fromXml(String xml) {
        return (ShuffleStimData) s.fromXML(xml);
    }

    public ShuffleType getShuffleType() {
        return shuffleType;
    }

    public void setShuffleType(ShuffleType shuffleType) {
        this.shuffleType = shuffleType;
    }
}