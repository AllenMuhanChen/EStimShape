package org.xper.sach.util;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Scanner;


public class SachIOUtil {

	public static char prompt(String str) {
		Scanner inputReader = new Scanner(System.in);
		System.out.print(str + ": ");
		char c = inputReader.next().charAt(0);
		//System.out.println(c);
		return c;
		
	}
	
	public static String promptString(String str) {
		Scanner inputReader = new Scanner(System.in);
		System.out.print(str + ": ");
		String s = inputReader.nextLine();
		return s;
	}
	
	public static char shortBool(boolean b) {
		if (b) return 'T';
		else return 'F';
	}
	
	private static final String YEARS_TO_MINUTES = "yyyy-MM-dd HH:mm";
	private static final SimpleDateFormat YEARS_TO_MINUTES_SDF = new SimpleDateFormat(YEARS_TO_MINUTES);

	public static String formatMicroSeconds(long timeMicroSeconds) {
	    String dateTime;
	    synchronized (YEARS_TO_MINUTES_SDF) {
	        dateTime = YEARS_TO_MINUTES_SDF.format(new Date(timeMicroSeconds / 1000));
	    }
	    long secs = timeMicroSeconds % 60000000;
	    return dateTime + String.format(":%09.6f", secs / 1e6);
	}
	
	public static long parseMicroSeconds(String text) throws ParseException {
	    long timeMS;
	    synchronized (YEARS_TO_MINUTES_SDF) {
	        timeMS = YEARS_TO_MINUTES_SDF.parse(text.substring(0, YEARS_TO_MINUTES.length())).getTime();
	    }
	    long microSecs = 0;
	    if (text.length() > YEARS_TO_MINUTES.length() + 1) {
	        double secs = Double.parseDouble(text.substring(YEARS_TO_MINUTES.length() + 1));
	        microSecs = (long) (secs * 1e6 + 0.5);
	    }
	    return timeMS * 1000 + microSecs;
	}
	
//	public static void main(String... args) throws ParseException {
//    String dateTime = "2011-01-17 19:27:59.999650";
//    long timeUS = parseMicroSeconds(dateTime);
//    for (int i = 0; i < 5; i++)
//        System.out.println(formatMicroSeconds(timeUS += 175));
//}
	
}


	
