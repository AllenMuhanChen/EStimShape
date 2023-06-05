package org.xper.fixtrain;

import com.thoughtworks.xstream.XStream;
import org.xper.drawing.Coordinates2D;
import org.xper.fixcal.CalibrationPointSetupMessage;

public class FixTrainCalibrationPointSetupMessage {
    Coordinates2D fixationPosition;
    String stimSpec;
    String stimClass;
    String size;

    public FixTrainCalibrationPointSetupMessage(Coordinates2D fixationPosition, String stimSpec, String stimClass, String size) {
        this.fixationPosition = fixationPosition;
        this.stimSpec = stimSpec;
        this.stimClass = stimClass;
        this.size = size;
    }

    public FixTrainCalibrationPointSetupMessage() {
    }

    static XStream xstream = new XStream();

    static {
        xstream.alias("CalibrationPointSetupMessage", FixTrainCalibrationPointSetupMessage.class);
    }

    public static FixTrainCalibrationPointSetupMessage fromXml(String xml) {
        return (FixTrainCalibrationPointSetupMessage) xstream.fromXML(xml);
    }

    public static String toXml(FixTrainCalibrationPointSetupMessage msg) {
        return xstream.toXML(msg);
    }

    public String toXml() {
        return xstream.toXML(this);
    }

    public Coordinates2D getFixationPosition() {
        return fixationPosition;
    }

    public void setFixationPosition(Coordinates2D fixationPosition) {
        this.fixationPosition = fixationPosition;
    }

    public String getStimSpec() {
        return stimSpec;
    }

    public void setStimSpec(String stimSpec) {
        this.stimSpec = stimSpec;
    }

    public String getStimClass() {
        return stimClass;
    }

    public void setStimClass(String stimClass) {
        this.stimClass = stimClass;
    }

    public String getSize() {
        return size;
    }

    public void setSize(String size) {
        this.size = size;
    }
}