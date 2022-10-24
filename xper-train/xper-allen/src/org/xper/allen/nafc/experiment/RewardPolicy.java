package org.xper.allen.nafc.experiment;

/*
 * LIST: reward only upon selecting any choice specified by a list in stimSpec
 * ANY: reward  upon selecting any choice
 * NONE: reward only upon selecting no choices. 
 * ALWAYS: reward no matter what, even if no choice is made
 */
public enum RewardPolicy {
	LIST, ANY, NONE, ALWAYS
	
}
