package org.xper.sach.util;

import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;


public class SachMapUtil {

	public static <K,V extends Comparable<? super V>> Map<K,V> sortByValue(Map<K,V> map) {
		List<Map.Entry<K, V>> list = new LinkedList<Map.Entry<K,V>>(map.entrySet());
		Collections.sort(list, new Comparator<Map.Entry<K,V>>() {
			public int compare(Map.Entry<K,V> o1, Map.Entry<K,V> o2) {
				return (o1.getValue()).compareTo(o2.getValue());
			}
		} );

		Map<K,V> result = new LinkedHashMap<K,V>();
		for (Map.Entry<K,V> entry : list) {
			result.put(entry.getKey(),entry.getValue());
		}
		return result;
	}

	public static void main(String[] args) {
		// to test it:
		
		Map<Long,Double> testMap = new HashMap<Long,Double>();
		
		for (long n = 10001;n<10006;n++) {
			testMap.put(n, SachMathUtil.randRange(10d,1d));
		}
		
		System.out.println(testMap);
		
		testMap = SachMapUtil.sortByValue(testMap);
		
		System.out.println(testMap);
		
	}
	
}



