package org.xper.sach.analysis;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.math.stat.descriptive.DescriptiveStatistics;
import org.xper.acq.counter.TrialStageData;
import org.xper.sach.util.SachMathUtil;
//import org.xper.sach.drawing.stimuli.BsplineObjectSpec;




import com.thoughtworks.xstream.XStream;

public class SachStimDataEntry {
	/**
	 * GA and firing rate information for a single stimulus object, for Beh objects we ignore parentage stuff
	 */
	
	// pre-runModeRun info:
	String trialType;									// "BEH" or "GA"
	int lineage = -1;									// for GA stim, the lineage in which it arose (prob 0 or 1)
	long birthGen = -1;									// for GA stim, the generation in which it first arose
	ArrayList<String> parentId;									// for GA stim, the parent stimObjId from which it was derived (-1 if no parent)
	long stimObjId;										// index into StimObjData db table
	String descriptiveId = ""; 
	
//	List<Long> stimSpecIds = new ArrayList<Long>();		// array of trials (indexed by StimSpec id) in which stim obj can be found
//	List<Long> taskToDoIds = new ArrayList<Long>();		// array of tasks (indexed by TaskToDo id) in which stim obj can be found
	
	// post-runModeRun info:
	List<Long> taskDoneIds = new ArrayList<Long>();							// array of tasks (indexed by TaskDone id) in which stim obj was presented

	Map<Integer, List<TrialStageData>> trialStageData = new HashMap<Integer,List<TrialStageData>>();
	Map<Integer,List<Double>> spikesPerSec = new HashMap<Integer,List<Double>>();
	Map<Integer,Double> sampleFrequency = new HashMap<Integer,Double>();
	
	Map<Integer,Double> avgFR = new HashMap<Integer,Double>();
	Map<Integer,Double> stdFR = new HashMap<Integer,Double>();
	
//	double avgBkgdFR = 0;	// this is calculated from any blank stimuli runModeRun in the same generation
//	double stdBkgdFR;
	
//	List<BsplineObjectSpec> stimObjSpecs = new ArrayList<BsplineObjectSpec>();	// stimulus details for each stimulus presentation (useful for Beh stimuli when morphing or randomizing limb lengths)

	
	transient static XStream s;
	
	static {
		s = new XStream();
		s.alias("Data", SachStimDataEntry.class);
		s.addImplicitCollection(String.class, "parentId");
//		s.addImplicitCollection(SachStimDataEntry.class, "objects", "object", SachStimDataEntry.class);
		
//		s.alias("limb", LimbSpec.class);
//		s.addImplicitCollection(BsplineObjectSpec.class, "limbs", "limb", LimbSpec.class);
	}

	public String toXml() {
		return SachStimDataEntry.toXml(this);
	}
	
	public static String toXml(SachStimDataEntry spec) {
		return s.toXML(spec);
	}
	
	public static SachStimDataEntry fromXml(String xml) {
		SachStimDataEntry g = (SachStimDataEntry)s.fromXML(xml);
		return g;
	}

	// setters & getters:
	
	public long getStimObjId() {
		return stimObjId;
	}
	public void setStimObjId(long stimObjId) {
		this.stimObjId = stimObjId;
	}
	public String getTrialType() {
		return trialType;
	}
	public void setTrialType(String type) {
		this.trialType = type;
	}
	public int getLineage() {
		return lineage;
	}
	public void setLineage(int lineage) {
		this.lineage = lineage;
	}
	public long getBirthGen() {
		return birthGen;
	}
	public void setBirthGen(long birthGen) {
		this.birthGen = birthGen;
	}
	public ArrayList<String> getParentId() {
		return parentId;
	}
	public void setParentId(ArrayList<String> parentId) {
		this.parentId = parentId;
	}
	
//	public List<Long> getStimSpecIds() {
//		return stimSpecIds;
//	}
//	public long getStimSpecId(int i) {
//		return stimSpecIds.get(i);
//	}
//	public void setStimSpecIds(List<Long> stimSpecIds) {
//		this.stimSpecIds = stimSpecIds;
//	}
//	public void addStimSpecId(long id) {
//		stimSpecIds.add(id);
//	}
//	
//	public List<Long> getTaskToDoIds() {
//		return taskToDoIds;
//	}
//	public long getTaskToDoId(int i) {
//		return taskToDoIds.get(i);
//	}
//	public void setTaskToDoIds(List<Long> taskToDoIds) {
//		this.taskToDoIds = taskToDoIds;
//	}
//	public void addTaskToDoId(long id) {
//		taskToDoIds.add(id);
//	}
	
	// data:
//	public double getSampleFrequency() {
//		return sampleFrequency;
//	}
//	public void setSampleFrequency(double sampleFrequency) {
//		this.sampleFrequency = sampleFrequency;
//	}
	
	public List<Long> getTaskDoneIds() {
		return taskDoneIds;
	}
	public long getTaskDoneId(int i) {
		return taskDoneIds.get(i);
	}
	public void setTaskDoneIds(List<Long> taskDoneIds) {
		this.taskDoneIds = taskDoneIds;
	}
	public void addTaskDoneId(long d) {
		taskDoneIds.add(d);
	}

//	public List<TrialStageData> getTrialStageData() {
//		return trialStageData;
//	}
//	public TrialStageData getTrialStageData(int i) {
//		return trialStageData.get(i);
//	}
//	public void setTrialStageData(List<TrialStageData> data) {
//		this.trialStageData = data;
//	}
//	public void addTrialStageData(TrialStageData d) {
//		trialStageData.add(d);
//	}
//	
//	public List<Double> getSpikesPerSec() {
//		return spikesPerSec;
//	}
//	public double getSpikesPerSec(int i) {
//		return spikesPerSec.get(i);
//	}
//	public void setSpikesPerSec(List<Double> spikesPerSec) {
//		this.spikesPerSec = spikesPerSec;
//		
//		setAvgFR(SachMathUtil.mean(spikesPerSec));
//		setStdFR(SachMathUtil.std(spikesPerSec));
//	}
//	public void addSpikesPerSec(double r) {
//		spikesPerSec.add(r);
//		
//		// also set the avg and std FRs:
//		DescriptiveStatistics stats = DescriptiveStatistics.newInstance();
//
//		for (int n=0;n<getNumPresentations();n++) {
//			stats.addValue(spikesPerSec.get(n));
//		}
//		
//		setAvgFR(stats.getMean());
//		setStdFR(stats.getStandardDeviation());
//	}

	public int getNumPresentations() {
		return taskDoneIds.size();
	}
	
//	public double getAvgFR() {
//		return avgFR;
//	}
//	public double getAvgFRminusBkgd() {
//		return avgFR-avgBkgdFR;
//	}
//	private void setAvgFR(double avgFR) {
//		this.avgFR = avgFR;
//	}
//	public double getStdFR() {
//		return stdFR;
//	}
//	private void setStdFR(double stdFR) {
//		this.stdFR = stdFR;
//	}
	
//	public List<Double> getBkgdSpikesPerSec() {
//		return bkgdSpikesPerSec;
//	}
//	public double getBkgdSpikesPerSec(int i) {
//		return bkgdSpikesPerSec.get(i);
//	}
//	public void setBkgdSpikesPerSec(List<Double> bkgdSpikesPerSec) {
//		this.bkgdSpikesPerSec = bkgdSpikesPerSec;
//		
//		setBkgdAvgFR(SachMathUtil.mean(bkgdSpikesPerSec));
//		setBkgdStdFR(SachMathUtil.std(bkgdSpikesPerSec));
//	}
//	public void addBkgdSpikesPerSec(double r) {
//		bkgdSpikesPerSec.add(r);
//		
//		setBkgdAvgFR(SachMathUtil.mean(bkgdSpikesPerSec));
//		setBkgdStdFR(SachMathUtil.std(bkgdSpikesPerSec));
//	}
//	
//	public double getBkgdAvgFR() {
//		return avgBkgdFR;
//	}
//	private void setBkgdAvgFR(double avgBkgdFR) {
//		this.avgBkgdFR = avgBkgdFR;
//	}
//	public double getBkgdStdFR() {
//		return stdBkgdFR;
//	}
//	private void setBkgdStdFR(double stdBkgdFR) {
//		this.stdBkgdFR = stdBkgdFR;
//	}
	
	// MULTICHANNEL
	public double getSampleFrequency(int channel) {
		return sampleFrequency.get(channel);
	}
	public void setSampleFrequency(double sampleFrequency, int channel) {
		this.sampleFrequency.put(channel, sampleFrequency);
	}
	public double getAvgFR(int channel) {
		return avgFR.get(channel);
	}
	private void setAvgFR(double avgFR, int channel) {
		this.avgFR.put(channel, avgFR);
	}
	public double getStdFR(int channel) {
		return stdFR.get(channel);
	}
	private void setStdFR(double stdFR, int channel) {
		this.stdFR.put(channel, stdFR);
	}
	
	public List<TrialStageData> getTrialStageData(int channel) {
		return trialStageData.get(channel);
	}
	public TrialStageData getTrialStageData(int trial, int channel) {
		return trialStageData.get(channel).get(trial);
	}
	public void setTrialStageData(List<TrialStageData> data,int channel) {
		this.trialStageData.put(channel, data);
	}
	public void addTrialStageData(TrialStageData d, int channel) {
		if (trialStageData.containsKey(channel))
			trialStageData.get(channel).add(d);
		else {
			trialStageData.put(channel, new ArrayList<TrialStageData>());
			trialStageData.get(channel).add(d);
		}
	}
	
	public List<Double> getSpikesPerSec(int channel) {
		return spikesPerSec.get(channel);
	}
	public double getSpikesPerSec(int trial, int channel) {
		return spikesPerSec.get(channel).get(trial);
	}
	public void setSpikesPerSec(List<Double> spikesPerSec, int channel) {
		this.spikesPerSec.put(channel, spikesPerSec);
		
		setAvgFR(SachMathUtil.mean(spikesPerSec),channel);
		setStdFR(SachMathUtil.std(spikesPerSec),channel);
	}
	public void addSpikesPerSec(double trialRate, int channel) {
		if (spikesPerSec.containsKey(channel))
			spikesPerSec.get(channel).add(trialRate);
		else {
			spikesPerSec.put(channel, new ArrayList<Double>());
			spikesPerSec.get(channel).add(trialRate);
		}
		
		// also set the avg and std FRs:
		DescriptiveStatistics stats = DescriptiveStatistics.newInstance();

		for (int n=0;n<spikesPerSec.get(channel).size();n++) {
			stats.addValue(spikesPerSec.get(channel).get(n));
		}
		
		setAvgFR(stats.getMean(),channel);
		setStdFR(stats.getStandardDeviation(),channel);
	}
}