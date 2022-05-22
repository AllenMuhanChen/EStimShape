package org.xper.allen.nafc.vo;

import org.xper.allen.drawing.composition.AllenMStickSpec;

import com.thoughtworks.xstream.XStream;

public class MStickStimObjData {
	String label;
	AllenMStickSpec spec;
	
	public MStickStimObjData(String label, AllenMStickSpec spec) {
		super();
		this.label = label;
		this.spec = spec;
	}

	static XStream s = new XStream();
	
	static {
		s.alias("MStickStimObjData", MStickStimObjData.class);
	}
	
	public static String toXml(MStickStimObjData data) {
		return s.toXML(data);
	}
	
	public String toXml() {
		return toXml(this);
	}

	public String getLabel() {
		return label;
	}

	public void setLabel(String label) {
		this.label = label;
	}

	public AllenMStickSpec getSpec() {
		return spec;
	}

	public void setSpec(AllenMStickSpec spec) {
		this.spec = spec;
	}
}
