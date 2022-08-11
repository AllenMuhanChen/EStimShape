package org.xper.sach.testing;

import java.util.ArrayList;
import java.util.List;

public class blah8 {

	/**
	 * @param args
	 */
	public static void main(String[] args) {

		List<Integer> arr1 = new ArrayList<Integer>();
		arr1.add(5);
		arr1.add(4);
		arr1.add(3);
		arr1.add(2);
		arr1.add(1);
		
		List<Integer> arr2 = new ArrayList<Integer>();
		arr2.add(6);
		arr2.add(5);
		arr2.add(7);
		arr2.add(8);
		arr2.add(2);
		arr2.add(1);
		arr2.add(0);
		
		System.out.println("arr1 = " + arr1.toString());
		System.out.println("arr2 = " + arr2.toString());

		// find all arr1 not in arr2:
		List<Integer> arr3 = new ArrayList<Integer>();
		arr3.addAll(arr1);
		arr3.removeAll(arr2);
		
		System.out.println("arr1 = " + arr1.toString());
		System.out.println("arr2 = " + arr2.toString());
		System.out.println("arr3 = " + arr3.toString());

		
	}

}
