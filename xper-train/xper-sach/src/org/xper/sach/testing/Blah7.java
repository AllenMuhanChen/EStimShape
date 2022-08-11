package org.xper.sach.testing;

import java.text.DateFormat;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;

import org.xper.sach.util.SachIOUtil;
import org.xper.time.DefaultTimeUtil;





public class Blah7 {


	public static void main(String[] args) throws ParseException {		

		System.out.println(System.getProperty("os.name"));
		System.out.println(OSValidator.isMac());
		
//		DefaultTimeUtil timer = new DefaultTimeUtil();
		
		
		
		
		DateFormat dateTimeFormat = new SimpleDateFormat("yyyy.MM.dd-HH.mm.ss.SSSSSS-z");
		Calendar cal = Calendar.getInstance();
//		String time2 = dateTimeFormat.format(currTime);
//		System.out.println(time2);
		System.out.println();

		long t0 = 1397215999405986L;
		System.out.println(t0);
		System.out.println(dateTimeFormat.format(t0));
		System.out.println(SachIOUtil.formatMicroSeconds(t0));
		
		System.out.println();
		
		long t2 = cal.getTimeInMillis() * 1000 + 981;
		System.out.println(t2);
		System.out.println(dateTimeFormat.format(t2));
		System.out.println(SachIOUtil.formatMicroSeconds(t2));

		System.out.println("--------------------------");

		
		 
		
		
		
	}

}

