package org.xper.sach.testing;

import java.util.ArrayList;
import java.util.List;


//import java.util.ArrayList;
//import java.util.Arrays;
//import java.util.Collection;
//import java.util.List;

//import org.xper.sach.training.drawing.stimuli.CircleSpecObject;
//import org.xper.sach.training.util.SachMathUtil;

//import com.mchange.v1.util.ArrayUtils;


public class EgadZooks {

	public enum Dir {
		NORTH, SOUTH, EAST, WEST
	}
	
	public static void main(String[] args) {
		Dir dir = Dir.NORTH;
		
		//System.out.println("was " + dir);
		
		if (dir == Dir.NORTH) {										// if (category = 3) randomly change to 1 or 2
			
			
			//System.out.println("now " + Dir.values()[(int)(Math.random()*2+1)]);
			//System.out.println("now " + Dir.values()[3]);
			
			//System.out.println("length " + Dir.values().length);

			//System.out.println("NORTH in int is " + Dir.EAST.ordinal());
		
		} else {
			System.out.println("oh boy");
		}
		
		
		//System.out.println("int " + Dir.NORTH.ordinal());
		//System.out.println("from int to enums " + Dir.values()[1]);
		
		Dir[] dirarr = {Dir.NORTH, Dir.EAST, Dir.WEST};
		System.out.println("arr length = " + dirarr.length);
		
		System.out.println("rand from arr = "+ dirarr[(int)(Math.random()*dirarr.length)]);

		//String strArr = enumArr2string(dirarr);
		
		System.out.println("Dir arr = " + enumArr2string(dirarr));
		
		Dir[] dirarr2 = removeElement(dirarr,Dir.EAST);
		System.out.println("Dir arr2 = " + enumArr2string(dirarr2));

		
		//int stimType = stimTypes[(int)(Math.random()*stimTypes.length)];
		
		

	}
	
	public static String enumArr2string(Enum[] eArr) {
		// make enum arr into string
		String result = "";
		for (int i=0; i<eArr.length; i++) {
			result += eArr[i].toString() + " ";
		}
		return result;
	}
	
	public static Dir[] removeElement(Dir[] s, Dir r) {
	    List<Dir> result = new ArrayList<Dir> ();
	    for (int i=0; i<s.length; i++) {
	        if (s[i] != r) {	// how do I compare StimColor enums here?
	            result.add(s[i]);
	        }
	    }

	    Dir[] toReturn = new Dir[result.size()];
	    for (int i=0; i<result.size(); i++) {
	        toReturn[i] = result.get(i);
	    }

	    return toReturn;
	}
	
}
