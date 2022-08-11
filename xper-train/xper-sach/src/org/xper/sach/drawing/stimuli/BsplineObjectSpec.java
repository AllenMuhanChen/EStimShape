package org.xper.sach.drawing.stimuli;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.util.ArrayList;
import java.util.List;

import com.thoughtworks.xstream.XStream;

public class BsplineObjectSpec {
	String stimType;
	ShapeMiscParams shape = new ShapeMiscParams();
	List<Aperture> masks = new ArrayList<Aperture>();
	Occluder occluder;

	transient static XStream s;

	static {
		s = new XStream();
		s.alias("StimSpec", BsplineObjectSpec.class);
		s.alias("shape", ShapeMiscParams.class);
		s.alias("mask", Aperture.class);
		s.alias("occluder", Occluder.class);

		s.alias("textureType", TextureType.class);
	}

	public String toXml() {
		return BsplineObjectSpec.toXml(this);
	}

	public static String toXml(BsplineObjectSpec spec) {
		return s.toXML(spec);
	}

	public static BsplineObjectSpec fromXml(String xml) {
		BsplineObjectSpec bsoSpec = (BsplineObjectSpec)s.fromXML(xml);
		return bsoSpec;
	}

	public void writeInfo2File(String fname) {
		//String fname = "./sample/nowStickInfo.txt";
		String outStr = this.toXml();
		try {
				BufferedWriter out = new BufferedWriter(new FileWriter(fname));
            	out.write(outStr);
	            out.flush();
	            out.close();
        } catch (Exception e) {
        	System.out.println(e);
    	}
	}

	public BsplineObjectSpec() {}

	public BsplineObjectSpec(BsplineObjectSpec d) {
		this.stimType = d.getStimType();
		this.shape = d.getShapeParams();
		this.masks = d.getApertures();
		this.occluder = d.getOccluder();
	}

	public String getStimType() {
		return stimType;
	}
	public void setStimType(String type) {
		this.stimType = type;
	}

	public ShapeMiscParams getShapeParams() {
		return shape;
	}

	public void setShapeParams(ShapeMiscParams shapeParams) {
		this.shape = shapeParams;
	}

	public List<Aperture> getApertures() {
		return masks;
	}

	public void setApertures(List<Aperture> aps) {
		this.masks = aps;
	}

	public Occluder getOccluder() {
		return occluder;
	}
	public void setOccluder(Occluder o) {
		this.occluder = o;
	}
}
