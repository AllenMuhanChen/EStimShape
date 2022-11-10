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

    public Map<String, Long> getGenIdForGA() {
        return genIdForGA;
    }

    public void setGenIdForGA(Map<String, Long> genIdForGA) {
        this.genIdForGA = genIdForGA;
    }
}
