package org.xper.sach.drawing.stick;

public class MAxisInfo
{
	public int nComponent;        
	public int nEndPt;
	public int nJuncPt;
	public double[] finalRotation = new double[3];
	public double shiftInDepth = 0.0;

	//public JuncPt_Info[] JuncPt;
	public EndPt_Info[] EndPt;
	public JuncPt_Info[] JuncPt;
    public TubeInfo[] Tube;
	//private TubeComp[] comp = new TubeComp[9];
	//private EndPt_struct[] endPt = new EndPt_struct[30]; // 30 is just an arbitrary large enough number
	//private JuncPt_struct[] JuncPt = new JuncPt_struct[30];	
	//private MStickObj4Smooth obj1;
	public void setMAxisInfo(MatchStick inStick)
	{
		int i;
		this.nComponent = inStick.nComponent;
		this.nEndPt = inStick.nEndPt;
		this.nJuncPt = inStick.nJuncPt;
		
		this.JuncPt = new JuncPt_Info[nJuncPt+1];
		this.EndPt  = new EndPt_Info[nEndPt+1];
		this.Tube = new TubeInfo[nComponent+1];
		for (i=1; i<= nEndPt; i++)
		{
			EndPt[i] = new EndPt_Info();
			EndPt[i].setEndPtInfo( inStick.endPt[i]);
			
		}
		for (i=1; i<= nJuncPt; i++)
		{
			JuncPt[i] = new JuncPt_Info();
			JuncPt[i].setJuncPtInfo( inStick.JuncPt[i]);
		}
		
		for (i=1; i<= nComponent; i++)
		{
			Tube[i] = new TubeInfo();
			Tube[i].setTubeInfo(inStick.comp[i]);
		}
		
		for (i=0; i<3; i++)
			finalRotation[i] = inStick.finalRotation[i];
		
		shiftInDepth = inStick.finalShiftinDepth.z;
		
	}
}