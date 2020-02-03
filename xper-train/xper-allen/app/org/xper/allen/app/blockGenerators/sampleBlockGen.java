package org.xper.allen.app.blockGenerators;

import org.xper.Dependency;
import org.xper.allen.Block;
import org.xper.allen.app.blockGenerators.trials.*;
import org.xper.allen.config.AllenDbUtil;
import org.xper.allen.specs.BlockSpec;

import com.thoughtworks.xstream.XStream;

public class sampleBlockGen {

	@Dependency
	AllenDbUtil dbUtil;
	
	int[] channel_list = {1};
	int num_per_chan;
	long blockId;
	trial[] trialList;
	BlockSpec blockspec;
	Block block;
	char[] trialTypeList;
	
	public sampleBlockGen(long blockId) {
		BlockSpec blockspec = dbUtil.readBlockSpec(blockId);
		Block block = new Block(blockspec);
		char[] trialTypeList = block.generateTrialList();
	}
	
	public trial[] generate() { //
		for (int i = 0; i < block.get_taskCount(); i++) {
			if (trialTypeList[i]=='c') {
				trialList[i] = new catchTrial();
			}
			else if (trialTypeList[i]=='v') {
				trialList[i] = new visualTrial(); 
			}
			else if (trialTypeList[i]=='e') {
				trialList[i] = new estimTrial();
			}
			else if (trialTypeList[i]=='b') {
				trialList[i] = new bothTrial();
			}
		}
		return trialList;
		
	}
	/*
	transient static XStream s;
	
	static {
		s = new XStream();
		s.alias("StimSpec", trial[].class);
	}
	
	public String toXml() {
		return sampleBlockGen.toXml(trialList);
	}
	
	public static String toXml (trial[] trialList) {
		return s.toXML(trialList);
	}
*/
}
