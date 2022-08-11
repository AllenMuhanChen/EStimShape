package org.xper.sach.util;

import java.text.DecimalFormat;

import org.xper.util.StringUtil;

public class SachStringUtil extends StringUtil {
	
	// added by -shs
	public static String format(double[] numArr, int n) {
		
		String out = "[";
		for (int k=0;k<numArr.length;k++) {
			double number = numArr[k];
			if (Double.isNaN(number) || Double.isInfinite(number)) {
				return String.valueOf(number);
			}
			DecimalFormat f = new DecimalFormat();
			f.setMaximumFractionDigits(n);
			String sep = (k==0) ? "" : ",";
			out = out + sep + f.format(number);	
		}
		return out + "]";
	}

}
