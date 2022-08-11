package org.xper.sach.testing;

//import java.util.ArrayList;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.TreeMap;
//import org.apache.commons.math3.stat.descriptive.moment.*;

import org.xper.sach.util.MyMathRepository;
import org.xper.sach.util.SachMapUtil;
import org.xper.sach.util.SachMathUtil;
import org.xper.sach.util.SachIOUtil;

public class Blah3 {

	static double[] percDivs = {0.3,0.5,0.7,0.9,1.0}; 			// percentile divisions: [0-.3), [.3-.5), [.5-.7), [.7-.9), [.9-1.0] 
	static double[] fracPerPercDiv = {0.1,0.15,0.2,0.2,0.35};	// probility per percentile division
	

	public static void main(String[] args) {		
		
		Map<Long, Double> testMap = new HashMap<Long, Double>();
//		testMap.put((long)10001,(double)10.0);
//		testMap.put((long)10002,(double)30.0);
//		testMap.put((long)10003,(double)5.0);
//		testMap.put((long)10004,(double)2.0);
		testMap.put(10001L,10d);
		testMap.put(10002L,2d);
		testMap.put(10003L,3d);
		testMap.put(10004L,5d);
		testMap.put(10005L,7d);
		testMap.put(10006L,15d);
		testMap.put(10007L,22d);
		testMap.put(10008L,8d);
		testMap.put(10009L,2d);
		testMap.put(10010L,6d);
		
//		System.out.println(testMap);
		
//		testMap = SachMapUtil.sortByValue(testMap);			
//
//		System.out.println(testMap);

		//List<Long> out = chooseStimsToMorph_FRdist(testMap);
		
//		List<Long> out = chooseStimsToMorph(testMap,100,2);
		
		//System.out.println(out);
//		int[] numEach = new int[2];
//		int x;
//		for (int n=0;n<1000;n++) {
//			x = (int)Math.round(Math.random());
//			System.out.print((int)Math.round(Math.random()));
//			if (x == 0) numEach[0]++;
//			else numEach[1]++;
//		}
//		System.out.println("\n numEach=" + Arrays.toString(numEach));
//		
		
		int[] p = SachMathUtil.randRange(1, 0, 20);
		System.out.println("r=" + Arrays.toString(p));

		int[] q = new int[20];
		for (int n=0;n<q.length;n++) {
			q[n] = SachMathUtil.randRange(1, 0);
		}
		System.out.println("r=" + Arrays.toString(q));

//		// find which nodes are end-nodes:
//		int numLimbs = 5;
//		int numNodes = numLimbs+1;
//		int[] nodesCxd = new int[]{-1, 0, 2, 3, 2};
////		for (int n=0;n<numLimbs;n++) { // for each limb, find the nodeId (that they connect to)
////			nodesCxd[n] = limbs.get(n).getNodeId();
////		}
//		List<Integer> endNodes = new ArrayList<Integer>();
//		boolean match;
//		for (int n=0;n<numNodes;n++) {	// find nodes that aren't cxd nodes
//			match = false;
//			for (int m=0;m<nodesCxd.length;m++) {
//				if (n == nodesCxd[m]) {
//					match = true;
//					break;
//				}
//			}
//			if (!match) endNodes.add(n);
//		}
//		System.out.println(endNodes);

	}

	public static List<Long> chooseStimsToMorph(Map<Long,Double> stim2FRmap, int numStimsToChoose, int method) {
		// choose which stimuli should be morphed based on thier firing rates
		// --- methods: 1 = by fixed probabilities by quintile
		// 				2 = by distance in firing rate space
		
		
		List<Long> stimsToMorph = new ArrayList<Long>();					// output array of stimObjIds to morph
		List<Long> allStimIds = new ArrayList<Long>(stim2FRmap.keySet());	// array of all available stimObjIds
		int numStims = allStimIds.size();
		long stimId = -1;
		Map<Long, Double> stimFitness = new HashMap<Long, Double>();		// the fitness value for each stim
		
		switch (method) {
		case 1:	// by fixed probabilities by quintile

			// sort stims by FR:
			stim2FRmap = SachMapUtil.sortByValue(stim2FRmap);			
			allStimIds = new ArrayList<Long>(stim2FRmap.keySet());	// redo after sort

			// divide stims into percentiles by FR:
				//	double[] percDivs = {0.3,0.5,0.7,0.9,1.0}; 		
				//	double[] fracPerPercDiv = {0.1,0.15,0.2,0.2,0.35};
			
//			// -- normalize FR:
//			// find max FR:
//			double maxFR = stim2FRmap.get(allStimIds.get(0));
//			double tmp;
//			for (int n=1;n<numStims;n++) {
//				tmp = stim2FRmap.get(allStimIds.get(n));
//				if (tmp > maxFR) {
//					maxFR = tmp;
//				}
//			}
//			// normalize:
//			for (int n=0;n<numStims;n++) {
//				stimId = allStimIds.get(n);
//				stimFitness.put(stimId,stim2FRmap.get(stimId)/maxFR);
//			}
//			System.out.println(stimFitness);
			
			// find rank order stim divisions: (***must be at least 6 stims for this to work given current percDivs***)
			int numPercDivs = percDivs.length;
			int[] stimsDivs = new int[numPercDivs];
			for (int n=0;n<numPercDivs;n++) {
				stimsDivs[n] = (int)Math.round(numStims*percDivs[n]);
			}
			//System.out.println(stim2FRmap);
			//System.out.println(Arrays.toString(stimsDivs));

			// assign probability based on FR quintile:
			int prevStimDiv, thisStimDiv;
			for (int n=0;n<numStims;n++) {
				stimId = allStimIds.get(n);
				prevStimDiv = 0;
				for (int m=0;m<numPercDivs;m++) {
					thisStimDiv = stimsDivs[m];
					if (stimsDivs[m] > n) {
						stimFitness.put(stimId,fracPerPercDiv[m]/(thisStimDiv-prevStimDiv));
						break;
					}
					prevStimDiv = thisStimDiv;
				}
			}
			//System.out.println(stimFitness);
			
			
//			// find number of stims in each quintile
//			int[] numPerDiv = new int[percDivs.length];
//			double normFR;
//			for (int n=0;n<numStims;n++) {
//				stimId = allStimIds.get(n);
//				normFR = stimFitness.get(stimId);
//				
//				for (int m=0;m<percDivs.length;m++) {
//					if (percDivs[m] >= normFR) {
//						numPerDiv[m]++;
//						break;
//					}
//				}
//			}
//			System.out.println(Arrays.toString(numPerDiv));
//
//			// assign probility/num stims in quintile
//			for (int n=0;n<numStims;n++) {
//				stimId = allStimIds.get(n);
//				normFR = stimFitness.get(stimId);
//				
//				for (int m=0;m<percDivs.length;m++) {
//					if (percDivs[m] >= normFR) {
//						stimFitness.put(stimId,fracPerPercDiv[m]/numPerDiv[m]);
//						break;
//					}
//				}
//			}
//			System.out.println(stimFitness);
//			
//			// check that they add to 1:
//			double tot = 0;
//			for (int n=0;n<numStims;n++) {
//				tot += stimFitness.get(allStimIds.get(n));
//			}
//			System.out.println("tot= " + tot);
//			

			break;
			
		case 2:	// by distance in firing rate space
			
			// -- find distance in FR space for each stim:
			double FRdist;
			for (int i=0;i<numStims;i++) {
				FRdist = 0;
				for (int j=0;j<numStims;j++) {
					// abs(FR of stim i - FR of stim j)
					FRdist += Math.abs(stim2FRmap.get(allStimIds.get(i))-stim2FRmap.get(allStimIds.get(j)));
				}
				stimFitness.put(allStimIds.get(i), FRdist);
			}

			// -- convert to fitness metric (normalize):
			// find total distance:
			double totalDist = 0;
			for (int n=0;n<numStims;n++) {
				totalDist += stimFitness.get(allStimIds.get(n));
			}
			// normalize:
			for (int n=0;n<numStims;n++) {
				stimId = allStimIds.get(n);
				stimFitness.put(stimId,stimFitness.get(stimId)/totalDist);
			}

//			// check that they add to 1:
//			totalDist = 0;
//			for (int n=0;n<numStims;n++) {
//				totalDist += stimFitness.get(allStimIds.get(n));
//			}
//			System.out.println("tot= " + totalDist);
			
			break;
		}
		
		
		// -- use fitness to choose stims:
		double x;
		double tmp;
		for (int n=0;n<numStimsToChoose;n++) {
			x = Math.random();
			tmp = 0;
			for (int m=0;m<numStims;m++) {
				stimId = allStimIds.get(m);
				tmp += stimFitness.get(stimId);
				if (x <= tmp) break;
			}
			stimsToMorph.add(stimId);
		}
		
		// check proportions of each stimuli chosen:
		int[] counts = new int[numStims];		
		for (int n=0;n<numStimsToChoose;n++) {
			stimId = stimsToMorph.get(n);
			int idx = (int)(stimId-10001);
			counts[idx]++;
		}
		Map<Long,Double> newMap = new TreeMap<Long,Double>(stim2FRmap);
		System.out.println(newMap);
		System.out.println(newMap.values());
		System.out.println(Arrays.toString(counts));
		
		return stimsToMorph;
	}
	
	public static List<Long> chooseStimsToMorph_FRdist(Map<Long,Double> stim2FRmap) {

		List<Long> stimsToMorph = new ArrayList<Long>();

		// find distance in FR space for each stim:
		Map<Long, Double> stimFRdist = new HashMap<Long, Double>();
		List<Long> stimIds = new ArrayList<Long>(stim2FRmap.keySet());
		int numStims = stimIds.size();
		
		double FRdist;
		for (int i=0;i<numStims;i++) {
			FRdist = 0;
			for (int j=0;j<numStims;j++) {
				// abs(FR of stim i - FR of stim j)
				FRdist += Math.abs(stim2FRmap.get(stimIds.get(i))-stim2FRmap.get(stimIds.get(j)));
			}
			stimFRdist.put(stimIds.get(i), FRdist);
		}
		System.out.println("FRdist= " + stimFRdist);

		// normalize for fitness metric:
			// find total distance:
		double totalDist = 0;
		for (int n=0;n<numStims;n++) {
			totalDist += stimFRdist.get(stimIds.get(n));
		}
		System.out.println("tot= " + totalDist);
			// normalize:
		long stimId = -1;
		for (int n=0;n<numStims;n++) {
			stimId = stimIds.get(n);
			stimFRdist.put(stimId,stimFRdist.get(stimId)/totalDist);
		}
		System.out.println("FRdist= " + stimFRdist);

//		totalDist = 0;
//		for (int n=0;n<numStims;n++) {
//			totalDist += stimFRdist.get(stimIds.get(n));
//		}
//		System.out.println("tot= " + totalDist);
		
		// use fitness to choose stims
		
		int numStims2Choose = 30;
		double x;
		double tmp;
		
		for (int n=0;n<numStims2Choose;n++) {
			
			x = Math.random();
			System.out.print("x=" +x);
			tmp = 0;
			for (int m=0;m<numStims;m++) {
				stimId = stimIds.get(m);
				tmp += stimFRdist.get(stimId);
				//System.out.print(" tmp=" +tmp);
				if (x < tmp) break;
			}
			stimsToMorph.add(stimId);
			System.out.println(" stimId=" +stimId);
		}
		System.out.println(stimsToMorph);
		
		int[] counts = new int[4];		
		for (int n=0;n<numStims2Choose;n++) {
			stimId = stimsToMorph.get(n);
			int idx = (int)(stimId-10001);
			counts[idx]++;
		}
		System.out.println(Arrays.toString(counts));
		
		return stimsToMorph;
	}
	
	
	public static double average(int[] data) {  
	    int sum = 0;
	    double average;

	    for(int i=0; i < data.length; i++){
	        sum = sum + data[i];
	    }
	    average = (double)sum/data.length;
	    return average;    
	}
	
//	Random r = new Random();
//	int[] ints = new int[10000];
//	
//	System.out.print("rand = ");
//	
//	for (int n = 1; n < ints.length; n++) {
//		ints[n] = r.nextInt(9)+1;
//		System.out.printf("%d ", ints[n]);
//
//	}
//	System.out.printf("\navg = %f", average(ints));
	
	
//	for (int n=0;n<40;n++) {
//		
//		int r = SachMathUtil.randRange(3,-1);
//		System.out.print(r + " ");
//
//	}
	
			
//	double[] vec1 = SachMathUtil.pol2vect(270,10);	// defined where ctr = [0,0]
//	double[] vec2 = SachMathUtil.pol2vect(91,1);
	
	//double ang = MyMath.getAngle(vec1,vec2);
	
	//vec1 = SachMathUtil.normVector(vec1);

	
//	double[] vec2 = new double[]{-2,0};
//	double[] vec1 = new double[]{0,2};
//	
//	System.out.println("vec1: x="+vec1[0]+" y="+vec1[1]+" mag=" + SachMathUtil.vectorMagnitude(vec1)+" ang="+SachMathUtil.vectorAngle(vec1));
//	System.out.println("vec2: x="+vec2[0]+" y="+vec2[1]+" mag=" + SachMathUtil.vectorMagnitude(vec2)+" ang="+SachMathUtil.vectorAngle(vec2));
//
//	// find bisecting angle
//	
//	System.out.println("bisecting angle=" + SachMathUtil.bisectingVector(vec1,vec2));
//	System.out.println("bisecting angle=" + (SachMathUtil.vectorAngle(new double[]{vec2[0]-vec1[0],vec2[0]-vec1[0]}) + 90));
//	System.out.println("bisecting angle=" + (SachMathUtil.vectorAngle(SachMathUtil.subtractVectors(vec2,vec1)) + 90));
//	
//	System.out.println("d= " + 1/Math.sin(90/2 * Math.PI/180));
//	
//	double[][] newB = new double[4][2];
//	
//	newB[1] = new double[]{33,22};
//	newB[2] = new double[]{33,22};
	
	

	// testing flanking indexes crap:
	
//	double x = 50;
//	double[] xarr = new double[]{45,300,105,30};
	
	//int[] idxs = flankingOriIdxs(x,xarr);
	
//	System.out.println("x=" + x + "  xarr =" + Arrays.toString(xarr));
//	System.out.println("idxLow=" + idxs[0] + "  idxHigh=" + idxs[1]);

	
//	Double a = (double)41*2*5/8;
//	System.out.println(a);
//	
//	int b=41,c=2,d=5,e=8;
//	
//	int out = (int)Math.ceil((double)b*c*d/e);
//	System.out.println(out);
	
	
//	List<Integer> l = new ArrayList<Integer>();
//	int numInts = 10;
//	
//	for (int n=0;n<numInts;n++) {
//		l.add(n);
//	}
//	
//	System.out.println(l.toString());
//	
//	// print groups of 3 until done
//	int k=0;
//	
//	for (int n=0;n<4;n++) {
//		
//		int s = k;
//		int e = k+3;
//		while (e>numInts) e--;
//		System.out.println(l.subList(s,e).toString());
//		k = e;
//	}
//	
//	int n = 0;
//	while(true) {
//		char c = SachIOUtil.prompt("To continue to generation " + 2 + " press (y) if not press (n)");
//		if (c == 'n') break;
//		System.out.println(n++);
//	}

}



