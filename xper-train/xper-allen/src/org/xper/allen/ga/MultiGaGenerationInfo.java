package org.xper.allen.ga;

import com.thoughtworks.xstream.XStream;
import org.xper.db.vo.MultiLineageGenerationInfo;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class MultiGaGenerationInfo {
    Map<String, Long> genIdForGA;

    transient static XStream s;

    static{
        s = new XStream();
        s.alias("GenerationInfo", MultiGaGenerationInfo.class);
    }

    public String toXml(){
        return MultiGaGenerationInfo.toXml(this);
    }

    public static String toXml(MultiGaGenerationInfo gaGenInfo){
        return s.toXML(gaGenInfo);
    }

    public static MultiGaGenerationInfo fromXml(String xml){
        MultiGaGenerationInfo g = (MultiGaGenerationInfo) s.fromXML(xml);
        return g;
    }

    public Map<String, Long> getGenIdForGA() {
        return genIdForGA;
    }

    public void setGenIdForGA(Map<String, Long> genIdForGA) {
        this.genIdForGA = genIdForGA;
    }
}
