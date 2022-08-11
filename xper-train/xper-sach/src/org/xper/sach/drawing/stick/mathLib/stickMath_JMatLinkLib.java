package org.xper.sach.drawing.stick.mathLib;

import jmatlink.JMatLink;

/**
 *  
 * @author aldenhung
 *  Include static function that relate to open, execute and close the JMatLink
 */
public class stickMath_JMatLinkLib {

	static JMatLink engine;
	static boolean engineOn = false;
	/**
	 * @param args
	 */
	public static void main(String[] args) {
		// TODO Auto-generated method stub
		
	}
	
	public static void engPut2DArray(String s, double[][] array)
	{
		engine.engPutArray(s, array);
	}
	
	public static void engPut1DArray(String s, double[] array)
	{
		engine.engPutArray(s, array);
	}
	
	public static double[][] engGetArray(String s)
	{
		return engine.engGetArray(s);
	}
	
	public static double engGetScalar(String s)
	{
		return engine.engGetScalar(s);
	}
	
	
	public static void eval(String s)
	{
		engine.engEvalString(s);
	}
	public static void startJMatEngine() 	
	{
		if (engineOn ) // no need to open again
			return;
		engineOn = true;
				
		engine = new JMatLink();		
		//engine.engOpen("matlab -nosplash");													
		//engine.engOpen();
		// In mac change to 
		engine.engOpen("/Users/aldenhung/bin/matlab");
		System.out.println("Start JMat engine -- Success");
	}
	
	
	public static void closeJMatLinkEngine()
	{
		if( engineOn )
		{
			engine.engClose();
			engineOn = false;
		}
	}

}
