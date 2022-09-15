package org.xper.sach.testing;

import java.util.ArrayList;
import java.util.List;


import org.xper.sach.util.SachIOUtil;


//import java.util.ArrayList;
//import java.util.Arrays;
//import java.util.Collection;
//import java.util.List;

//import org.xper.sach.training.drawing.stimuli.CircleSpecObject;
//import org.xper.sach.training.util.SachMathUtil;

//import com.mchange.v1.util.ArrayUtils;


public class BlahTest2 {

	public enum Dir {
		NORTH, SOUTH, EAST, WEST
	}
	
	public static void main(String[] args) {
//		Dir dir = null;
				
//		System.out.println("was " + dir);
//		
//		if (dir == Dir.NORTH) {										// if (category = 3) randomly change to 1 or 2
//			
//			
//			System.out.println("now " + Dir.values()[(int)(Math.random()*2+1)]);
//
//			System.out.println("&now " + Dir.values().length);
//
//		
//		} else {
//			System.out.println("oh boy");
//		}
		
//		String stimClass = "woot";
//		if (stimClass == "woot") {
//			System.out.println(stimClass);
//		}

		
//		System.out.println("east= " + Dir.EAST.ordinal());
//		System.out.println("east= " + Dir.valueOf("EAST").ordinal());
//
//		System.out.println("cat= " + Dir.values()[0]);
//		System.out.println("cat= " + Dir.values()[1]);
//		System.out.println("cat= " + Dir.values()[2]);
		
		
//		int n = 20;
//		if (0 <= n & n < Dir.values().length) {
//			dir = Dir.values()[n];
//		} 
//		
//		System.out.println("cat= " + dir);
//
//		if (dir == null) {
//			System.out.println("hell");
//		}
		
//		Dir bb = null;
//		System.out.println("cat= " + bb);
		
		// other test:
		
//		List<LimbSpec> limbs = new ArrayList<LimbSpec>();
//		limbs = null;
//
//		if (limbs.size() > 0) {
//			System.out.println("uh no");
//		} else {
//			System.out.println("# limbs = " + limbs.size());
//		}
		
		
		// -- create and write to text file:
	char c = SachIOUtil.prompt("Which Behavioral task is this?" + 
			"\n  (t) training runModeRun" + 					// then ask which morph line level (0 to 1)
			"\n  (m) morph line experimental runModeRun" +		// then ask which morph line level (using SD of exp, gamma, Gaussian distribution?), and ask which group of 4 categories to runModeRun
			"\n  (q) quick characterization of category preference" +
			"\n");
	
	switch (c) {
	case 't':	// training runModeRun
		System.out.println(c);

		break;
		
	case 'm':	// morph line experimental runModeRun
		System.out.println(c);

		break;
		
	case 'q':	// quick characterization for finding "preferred" category
		System.out.println(c);

		break;

	default:	// otherwise exit
		System.out.println("WARNING: '" + c + "' is not a valid entry. Exiting.");
		break;
	}
	
		
	}
	
}
