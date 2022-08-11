package org.xper.sach.expt;

import java.util.ArrayList;
import java.util.List;

//import org.xper.drawing.Coordinates2D;
import org.xper.sach.drawing.stimuli.BsplineObjectSpec;

import com.thoughtworks.xstream.XStream;

public class SachExptSpec {
	String trialType;
//	Coordinates2D targetPosition = new Coordinates2D();
//	double targetEyeWinSize;
	long reward;
//	long targetIndex;
//	List<BsplineObjectSpec> objects = new ArrayList<BsplineObjectSpec>();
	List<Long> objects = new ArrayList<Long>();

	// The units of targetPosition and targetEyeWinSize have to be in degrees

	
	transient static XStream s;
	
	static {
		s = new XStream();
		s.alias("StimSpec", SachExptSpec.class);
		s.alias("object", BsplineObjectSpec.class);
//		s.useAttributeFor("animation", boolean.class);
//		s.alias("targetPosition", Coordinates2D.class);
//		s.addImplicitCollection(SachExptSpec.class, "objects", "object", BsplineObjectSpec.class);
		s.addImplicitCollection(SachExptSpec.class, "objects", "object", Long.class);
		
//		s.alias("limb", LimbSpec.class);
//		s.addImplicitCollection(BsplineObjectSpec.class, "limbs", "limb", LimbSpec.class);
	}
	
//	public void addObjectSpec(BsplineObjectSpec spec) {
//		objects.add(spec);
//	}
//	
//	public BsplineObjectSpec getObjectSpec(int index) {
//		if (index < 0 || index >= objects.size()) {
//			return null;
//		} else {
//			return objects.get(index);
//		}
//	}
//	
//	public int getObjectSpecCount() {
//		return objects.size();
//	}
	
	public void addStimObjId(long id) {
		objects.add(id);
	}
	
	public long getStimObjId(int index) {
		if (index < 0 || index >= objects.size()) {
			return -1;
		} else {
			return objects.get(index);
		}
	}
	
	public int getStimObjIdCount() {
		return objects.size();
	}
	
	public String toXml() {
		return SachExptSpec.toXml(this);
	}
	
	public static String toXml(SachExptSpec spec) {
		return s.toXML(spec);
	}
	
	public static SachExptSpec fromXml(String xml) {
		SachExptSpec g = (SachExptSpec)s.fromXML(xml);
		return g;
	}

//	public Coordinates2D getTargetPosition() {
//		return targetPosition;
//	}
//
//	public void setTargetPosition(Coordinates2D targetPosition) {
//		this.targetPosition = targetPosition;
//	}
//
//	public double getTargetEyeWinSize() {
//		return targetEyeWinSize;
//	}
//
//	public void setTargetEyeWinSize(double targetEyeWinSize) {
//		this.targetEyeWinSize = targetEyeWinSize;
//	}

	public long getReward() {
		return reward;
	}

	public void setReward(long reward) {
		this.reward = reward;
	}

//	public long getTargetIndex() {
//		return targetIndex;
//	}
//
//	public void setTargetIndex(long targetIndex) {
//		this.targetIndex = targetIndex;
//	}

	public String getTrialType() {
		return trialType;
	}

	public void setTrialType(String trialType) {
		this.trialType = trialType;
	}
}
