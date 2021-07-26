package org.xper.allen.twoac;

/*
 * ONE: reward only upon selecting choice "one"
 * TWO: reward only upon selecting choice "two'
 * EITHER: reward upon selecting either choice "one" or "two". No reward upon failed selection
 * NONE: reward only upon not selecting any choice. 
 * ANY: reward no matter what
 */
public enum RewardPolicy {
	ONE, TWO, EITHER, NONE, ANY
	
}
