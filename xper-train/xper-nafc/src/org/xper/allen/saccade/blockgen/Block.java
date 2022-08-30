package org.xper.allen.saccade.blockgen;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Random;

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
		Random rand = new Random();
		//trialList: c-catch trial, v-vstim only, e-estim only, b-both
		trialList = new char[taskCount];
		Arrays.fill(trialList, 0, block.get_num_catches(), 'c');
		Arrays.fill(trialList, block.get_num_catches(), block.get_num_catches()+block.get_num_stims_only(), 'v');
		Arrays.fill(trialList, block.get_num_catches()+block.get_num_stims_only(), block.get_num_catches()+block.get_num_stims_only()+block.get_num_estims_only(), 'e');		
		Arrays.fill(trialList, block.get_num_catches()+block.get_num_stims_only()+block.get_num_estims_only(), block.get_num_catches()+block.get_num_stims_only()+block.get_num_estims_only()+block.get_num_both(), 'b');	
		if (block.get_shuffle().equals("yes")) {
			System.out.println("entered shuffle if statement");
			for (int i =0; i < trialList.length; i++) {
				int randomIndexToSwap = rand.nextInt(trialList.length);
				char temp = trialList[randomIndexToSwap];
				trialList[randomIndexToSwap] = trialList[i];
				trialList[i] = temp;
			}
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
