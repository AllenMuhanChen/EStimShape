package org.xper.sach.util;


import java.util.ArrayList;
import java.util.Random;

//Bias Random number generator
//see static function test() for example use -
//johnny Wilson 

public class BiasRandom {
	static Random DEFAULTRNG = new Random(1235) ;
	ArrayList<Double> prob = new ArrayList<Double>();	
	double sum = 0;
	Random random = new Random();
	
	public BiasRandom() {
		this(new Random());
	}
	// Allows you to define uniform Random number generator
	// to be used.
	
	public BiasRandom(Random rng) {
		random = rng;
	}
	
	public BiasRandom(Random rng,double[] numbers) {
		random = rng;
		defineDistArray(numbers);
	}
	
	public BiasRandom(double[] numbers) {
		this(new Random(),numbers);
	}
	
	
	public void addValue(double num) {
		sum = sum + num;
		prob.add(new Double(num));
	}
	
	public void defineDist(double... numbers) {
		prob = new ArrayList<Double>();	
		sum = 0;
		for(double num : numbers) {
			addValue(num);
		}
	}
	
	public void defineDistArray(double[] numbers) {
		prob = new ArrayList<Double>();	
		sum = 0;
		for (int i=0; i<numbers.length; i++) {
			addValue(numbers[i]);
		}
	}
	
	public double getSum() {
		return sum;
	}
	
	// selectEvent 
	// Given a List of % probabilities of a particular event
	// Returns - a Random index - weighted by that table
	// Eg. int [] eventdistTable = {50,25,10,15}
	// Gives 10% chance of returning 0 
	// Gives 25% chance of returning 1
	// Gives 50% chance of returning 2
	// Gives 15% chance of returning 3
	
	// NB: Sum of eventdistTable elements must work out to be 100
	//  If it doesn't then % chances are worked out
	//  over the sum of elements in eventdistTable
	// Probability table is set up by the helper functions
	// defineDist(double... numbers) or defineDistArray(double[] numbers)
	// See test() for example
	
	
	public int selectEvent() {
		int index = 0;
		double cummSum = 0.0;
		double rnd = (double)(1 + random.nextInt((int)sum)); // why does this round off to integers??
		while(true) {
			cummSum = cummSum + prob.get(index);
			if (rnd <= cummSum) {
				return index;
			} 
			index = index + 1;
		}
	}
	
	public static void test() {
			//double[] dist = {10,15,50,25};
			double[] dist = { 0.999, 1, 4, 2 };
			BiasRandom br = new BiasRandom(dist);
			// note: above two lines can be replaced with 
			// BiasRandom br = new BiasRandom(dist);
			
			int[] history = new int[dist.length];
			int numThrows = 10000000;
			for (int i=0; i<numThrows; i++) {
				int ev = br.selectEvent();
				history[ev] = history[ev] + 1;
			}
	
			int sum = 0;
			for (int i = 0; i < history.length; i++) {
				sum = sum + history[i];
				System.out.printf("Event %d percentage selected %f\n",i,(100.0 * history[i])/numThrows);
			}
			System.out.printf("Total %d\n",sum);
	}
	
	public static void main(String[] args) {
		test();
	}
	
}

