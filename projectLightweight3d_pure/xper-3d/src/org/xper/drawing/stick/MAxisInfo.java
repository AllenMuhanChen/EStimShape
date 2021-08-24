package org.xper.drawing.stick;

public class MAxisInfo {
	public int nComponent;        
	public int nEndPt;
	public int nJuncPt;
	public double[] finalRotation = new double[3];
	public double[] finalShiftInDepth = new double[3];
	public EndPt_Info[] EndPt;
	public JuncPt_Info[] JuncPt;
    public TubeInfo[] Tube;

	public void setMAxisInfo(MatchStick inStick) {
		nComponent = inStick.getNComponent();
		nEndPt = inStick.getNEndPt();
		nJuncPt = inStick.getNJuncPt();
		
		JuncPt = new JuncPt_Info[nJuncPt+1];
		EndPt  = new EndPt_Info[nEndPt+1];
		Tube = new TubeInfo[nComponent+1];
		
		for (int i=1; i<= nEndPt; i++) {
			EndPt[i] = new EndPt_Info();
			EndPt[i].setEndPtInfo(inStick.getEndPtStruct(i));
		}
		for (int i=1; i<= nJuncPt; i++) {
			JuncPt[i] = new JuncPt_Info();
			JuncPt[i].setJuncPtInfo( inStick.getJuncPtStruct(i));
		}
		for (int i=1; i<= nComponent; i++) {
			Tube[i] = new TubeInfo();
			Tube[i].setTubeInfo(inStick.getTubeComp(i));
		}
		
		for (int i=0; i<3; i++)
			finalRotation[i] = inStick.getFinalRotation(i);
		
		for (int i=0; i<3; i++)
			finalShiftInDepth[i] = inStick.getFinalShiftInDepth(i);
	}
}