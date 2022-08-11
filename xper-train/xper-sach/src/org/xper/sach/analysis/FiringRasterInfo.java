package org.xper.sach.analysis;
/**
 *   
 * 	@author r1_aldenhung
 *	Dec 14th 2008
 *	This is a class use to store the firing informatino
 *  Both the avg/std firing rate and also
 *  The detailed firing time stamp
 */
public class FiringRasterInfo {
	double avgFiringRate;
	double standardDev;
	int nTrial = 0;
	int maxTrialLen;
	double[] spikeRate = new double[100];
	int[] nSpike = new int[100]; // this mean at most 100 trials
	int[] trialLen = new int[100];
	int[][] spikeEntry = new int[100][1000]; // at most 1000 spk in a trial
	
	int rate_Nano = 40; // this means the sampling rate is 40nano second
	  // i.e. the ACQ require data at 25000 Hz rate
	/**
	 *   every time we read in a new task ( a new trial)
	 *   We update the info stored here
	 */
	public void addTrial(int[] spk_list, int startTime, int endTime, double spkRate)
	{
		//store the nSpike and spikeEntry
		int i;
		int ndx = nTrial;
		nSpike[ndx] = spk_list.length;
		for (i=0; i< nSpike[ndx]; i++)
			spikeEntry[ndx][i] = (spk_list[i] - startTime) * rate_Nano;		
		
		spikeRate[ndx] = spkRate;
		
		trialLen[ndx] = (endTime - startTime ) * rate_Nano;
		if ( trialLen[ndx] > this.maxTrialLen)
			maxTrialLen = trialLen[ndx];
		nTrial++;		
		//update avg/std
		double sum = 0;
		for (i=0; i < nTrial; i++)
			sum += spikeRate[i];
		this.avgFiringRate = sum / (double)nTrial;
		
		this.updateStd();				
	}
	//calculate the standard variation
	private void updateStd()
	{
		int i;
		double sum = 0.0;
		for (i=0; i< nTrial; i++)
				sum += (spikeRate[i] - avgFiringRate) *(spikeRate[i] - avgFiringRate);
		sum /= nTrial;
		this.standardDev = Math.sqrt(sum);		
	}
}
