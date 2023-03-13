package org.xper.allen.ga;

import com.thoughtworks.xstream.XStream;

public class StimGaInfo {
    long stimId;
    long parentId;
    String gaName;
    long genId;
    long lineageId;
    String treeSpec;
    String stimType;

    public StimGaInfo() {
    }

    private static final XStream s;

    static {
        s = new XStream();
        s.alias("StimGaInfo", StimGaInfo.class);
    }

    public static StimGaInfo fromXml(String xml) {
        return (StimGaInfo) s.fromXML(xml);
    }

    public String toXml() {
        return s.toXML(this);
    }

    public static String toXml(StimGaInfo stimGaInfo) {
        return s.toXML(stimGaInfo);
    }

    public long getStimId() {
        return stimId;
    }

    public void setStimId(long stimId) {
        this.stimId = stimId;
    }

    public long getParentId() {
        return parentId;
    }

    public void setParentId(long parentId) {
        this.parentId = parentId;
    }

    public String getGaName() {
        return gaName;
    }

    public void setGaName(String gaName) {
        this.gaName = gaName;
    }

    public long getGenId() {
        return genId;
    }

    public void setGenId(long genId) {
        this.genId = genId;
    }

    public long getLineageId() {
        return lineageId;
    }

    public void setLineageId(long lineageId) {
        this.lineageId = lineageId;
    }

    public String getTreeSpec() {
        return treeSpec;
    }

    public void setTreeSpec(String treeSpec) {
        this.treeSpec = treeSpec;
    }

    public String getStimType() {
        return stimType;
    }

    public void setStimType(String stimType) {
        this.stimType = stimType;
    }
}