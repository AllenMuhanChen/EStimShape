package org.xper.allen.nafc.blockgen.procedural;

import com.thoughtworks.xstream.XStream;

import java.util.List;
import java.util.Map;

public class MixedParams {

    Map<ProceduralRandGenParameters, String> paramsForGenTypes;


    public MixedParams(Map<ProceduralRandGenParameters, String> paramsForGenTypes) {
        this.paramsForGenTypes = paramsForGenTypes;
    }

    public MixedParams() {
    }

    static XStream xstream = new XStream();

    public String toXml(){
        return xstream.toXML(this);
    }

    public static MixedParams fromXml(String xml){
        return (MixedParams) xstream.fromXML(xml);
    }
}