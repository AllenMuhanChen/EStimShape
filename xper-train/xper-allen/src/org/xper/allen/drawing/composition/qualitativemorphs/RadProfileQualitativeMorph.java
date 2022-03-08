package org.xper.allen.drawing.composition.qualitativemorphs;

import java.util.List;

public class RadProfileQualitativeMorph extends QualitativeMorph{
	private boolean juncFlag;
	private boolean midFlag;
	private boolean endFlag;
	
	private double oldJunc;
	private double oldMid;
	private double oldEnd;
	
	private double newJunc;
	private double newMid;
	private double newEnd;
	
	private List<Bin<Double>> juncBins;
	private List<Bin<Double>> midBins;
	private List<Bin<Double>> endBins;
	
	private int assignedJuncBin;
	private int assignedMidBin;
	private int assignedEndBin;
	
	
}
