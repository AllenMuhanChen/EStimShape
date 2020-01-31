package org.xper.allen;

import java.util.Arrays;

import org.xper.allen.specs.BlockSpec;

public class Block {
	//Variable Declarations
	int taskCount;
	BlockSpec block;
	char trialList[];
	
	//Constructors
	public Block(int taskCount, BlockSpec block) { //Specify taskCount manually
		this.taskCount = taskCount;
		this.block = block;
	}
	
	public Block(BlockSpec block) { //fetch taskCount from BlockSpec
		this.block = block;
		this.taskCount = fetchTaskCount();
	}
	 
	//Methods
	public int fetchTaskCount(){
		return block.get_num_catches()+block.get_num_estims_only()+block.get_num_stims_only()+block.get_num_both();
	}
	
	public char[] generateTrialList() {
		//trialList: c-catch trial, v-vstim only, e-estim only, b-both
		trialList = new char[taskCount];
		Arrays.fill(trialList, 0, block.get_num_catches()-1, 'c');
		Arrays.fill(trialList, block.get_num_catches(), block.get_num_catches()+block.get_num_stims_only()-1, 'v');
		Arrays.fill(trialList, block.get_num_catches()+block.get_num_stims_only(), block.get_num_catches()+block.get_num_stims_only()+block.get_num_estims_only()-1, 'e');		
		Arrays.fill(trialList, block.get_num_catches()+block.get_num_stims_only()+block.get_num_estims_only(), block.get_num_catches()+block.get_num_stims_only()+block.get_num_estims_only()+block.get_num_both()-1, 'b');	
		if (block.get_shuffle() == "yes") {
			//Shuffle Code Here	
			}
		return trialList;
	}
	
	public char[] get_trialList( ) {
		return trialList;
	}

	public int get_taskCount( ) {
		return taskCount;
	}
	
	public BlockSpec get_blockSpec() {
		return block;
	}
	
	
}
