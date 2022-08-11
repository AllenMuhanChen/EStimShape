package org.xper.sach.testing;

//import java.util.ArrayList;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Random;

import org.springframework.beans.factory.annotation.Autowired;
import org.xper.config.AcqConfig;
import org.xper.time.SocketTimeClient;

public class testing_shuffle {

	@Autowired AcqConfig acqConfig;

	
	public static void main(String[] args) {		
	
		String questions[] = {
				"Q0?",
				"Q1?",
				"Q2?"
		};

		String answers[] = {
				"A0?",
				"A1?",
				"A2?"
		};
		
		List<String> qs = Arrays.asList("0","1","2","3","4","5","6","7","8");
		List<String> as = Arrays.asList("0","1","2","3","4","5","6","7","8");
		
//		List<Integer> indexArray = Arrays.asList(0, 1, 2);
//		System.out.println("original: " + indexArray.toString());
//
//		
//		Collections.shuffle(indexArray);
//
//		String question = questions[indexArray.get(0)];
//		String answer = answers[indexArray.get(0)];
//
//		System.out.println("shuffled: " + indexArray.toString());
//		
//		System.out.println("q: " + question + "   a: " + answer);
		
		long l = System.currentTimeMillis();		
		
		System.out.println(qs.toString());
		Collections.shuffle(qs,new Random(l));
		Collections.shuffle(as,new Random(l));

		System.out.println(qs.toString());
		System.out.println(as.toString());
		
	}
	

}



