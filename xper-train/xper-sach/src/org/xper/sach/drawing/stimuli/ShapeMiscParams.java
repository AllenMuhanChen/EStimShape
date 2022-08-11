package org.xper.sach.drawing.stimuli;

import org.xper.drawing.RGBColor;
import org.xper.sach.drawing.splines.MyPoint;

public class ShapeMiscParams {

	MyPoint pos;
	double size;

	RGBColor color;
	TextureType textureType;
	
	boolean doClouds;
    boolean lowPass = true;
    boolean saveVertSpec = false;
    
    int radiusProfile = 0;
    
	boolean tagForRand = false;
	boolean tagForMorph = false;
	
	boolean isOccluded = true;
	
	MyPoint lightingPos;

	public ShapeMiscParams() {
		pos = new MyPoint(0, 0);
		size = 1.0;
		
		color = new RGBColor(1,1,1);
		textureType = TextureType.SHADE;
		
		lightingPos = new MyPoint(0, 100, 200);
		
		doClouds = false;
		isOccluded = false;
		lowPass = false;
		saveVertSpec = false;
		
		radiusProfile = 0;
		
		tagForMorph = false;
		tagForRand = false;
	}

	public ShapeMiscParams(MyPoint pos, double size, RGBColor color, 
			TextureType tt, boolean doClouds, boolean isOccluded, 
			boolean tagForRand, boolean tagForMorph, boolean lowPass,
			MyPoint lightingPos, boolean saveVertSpec, int radiusProfile) {
		this.pos = pos;
		this.size = size;
		this.color = color;
		this.textureType = tt;
		this.doClouds = doClouds;
		this.tagForMorph = tagForMorph;
		this.tagForRand = tagForRand;
		this.isOccluded = isOccluded;
		this.lowPass = lowPass;
		this.lightingPos = lightingPos;
		this.saveVertSpec = saveVertSpec;
		this.radiusProfile = radiusProfile;
	}

	public RGBColor getColor() {
		return color;
	}
	public void setColor(RGBColor color) {
		this.color = color;
	}

	public TextureType getTextureType() {
		return textureType;
	}
	public void setTextureType(TextureType textureType) {
		this.textureType = textureType;
	}

	public MyPoint getPos() {
		return pos;
	}
	public void setPos(MyPoint pos) {
		this.pos = pos;
	}

	public double getSize() {
		return size;
	}
	public void setSize(double size) {
		this.size = size;
	}

	public void setTagForMorph(boolean tag) {
		this.tagForMorph = tag;
	}
	public boolean getTagForMorph() {
		return this.tagForMorph;
	}

	public void setTagForRand(boolean tag) {
		this.tagForRand = tag;
	}
	public boolean getTagForRand() {
		return this.tagForRand;
	}
	public void setDoClouds(boolean doClouds) {
		this.doClouds = doClouds;
	}
	public boolean getDoClouds() {
		return this.doClouds;
	}
	public void setLowPass(boolean lowPass) {
		this.lowPass = lowPass;
	}
	public boolean getLowPass() {
		return this.lowPass;
	}
	public void setSaveVertSpec(boolean saveVertSpec) {
		this.saveVertSpec = saveVertSpec;
	}
	public boolean getSaveVertSpec() {
		return this.saveVertSpec;
	}
	
	public MyPoint getLightingPos() {
		return lightingPos;
	}
	public void setLightingPos(MyPoint lightingPos) {
		this.lightingPos = lightingPos;
	}
	
	public int getRadiusProfile() {
		return radiusProfile;
	}
	public void setRadiusProfile(int radiusProfile) {
		this.radiusProfile = radiusProfile;
	}
}
