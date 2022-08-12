package org.xper.util;

import java.text.DecimalFormat;

public class StringUtil {
	/**
	 * pad a string S with a size of N with char C on the left (True) or on the
	 * right(false)
	 */
	public static String pad(String s, int n, char c,
			boolean paddingLeft) {
		StringBuffer str = new StringBuffer(s);
		int strLength = str.length();
		if (n > 0 && n > strLength) {
			for (int i = 0; i <= n; i++) {
				if (paddingLeft) {
					if (i < n - strLength)
						str.insert(0, c);
				} else {
					if (i > strLength)
						str.append(c);
				}
			}
		}
		return str.toString();
	}
	
	/**
	 * 
	 * @param number
	 * @param n digits after decimal point
	 * @return
	 */
	public static String format(double number, int n) {
		if (Double.isNaN(number) || Double.isInfinite(number)) {
			return String.valueOf(number);
		}
		DecimalFormat f = new DecimalFormat();
		f.setMaximumFractionDigits(n);
		return f.format(number);
	}

}
