package org.xper.allen.specs;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.png.ImageDimensions;
import org.xper.drawing.stick.EndPt_Info;
import org.xper.drawing.stick.JuncPt_Info;
import org.xper.drawing.stick.MAxisArc;
import org.xper.drawing.stick.MStickSpec;
import org.xper.drawing.stick.TubeComp;
import org.xper.drawing.stick.TubeInfo;

import com.thoughtworks.xstream.XStream;

public class AllenMStickSpec extends MStickSpec{

	double minSize;
	double maxSize;
	
    transient static XStream s;

    static {
        s = new XStream();
        s.alias("MStickSpec", AllenMStickSpec.class);
        s.alias("EndPtInfo", EndPt_Info.class);
        s.alias("JuncPtInfo", JuncPt_Info.class);
        s.alias("TubeInfo", TubeInfo.class);   
    }
    
    public String toXml () {
        return MStickSpec.toXml(this);
    }

    public static String toXml (AllenMStickSpec spec) {
        return s.toXML(spec);
    }
    
    public static AllenMStickSpec fromXml (String xml) {
        AllenMStickSpec g = (AllenMStickSpec)s.fromXML(xml);
        return g;
    }

    public void setMStickInfo( AllenMatchStick inStick)
    {
		getmAxis().setMAxisInfo(inStick);
		vertex.setVertexInfo(inStick.getSmoothObj());

        TubeComp[] tubes = inStick.getComp();
        
        compPosTanStr = "";
        for (int i=1; i<=getNComponent(); i++) {
            MAxisArc tempArc = tubes[i].getmAxisInfo();
            compPosTanStr = compPosTanStr + i + "," + i + "," + i + "," + 
                    tempArc.curvature + "," + tempArc.getArcLen() + "," + tempArc.getRad() + "\n";
            for (int j=1; j<=51; j++) {
                compPosTanStr = compPosTanStr + tempArc.getmPts()[j].x + "," + tempArc.getmPts()[j].y + "," + 
                        tempArc.getmPts()[j].z + "," + tempArc.getmTangent()[j].x + "," + 
                        tempArc.getmTangent()[j].y + "," + tempArc.getmTangent()[j].z + "\n";
                
                
            }
        }
    }

	public double getMinSize() {
		return minSize;
	}

	public void setMinSize(double minSize) {
		this.minSize = minSize;
	}

	public double getMaxSize() {
		return maxSize;
	}

	public void setMaxSize(double maxSize) {
		this.maxSize = maxSize;
	}
    


}