package org.xper.rfplot.drawing.png;

import java.awt.geom.Dimension2D;

public class ImageDimensions extends Dimension2D {
	double width;
	double height;
    public ImageDimensions() {
    }
    public ImageDimensions(double width, double height) {
    	this.width = width;
    	this.height = height;
    }
    
    public void setSize(Dimension2D d) {
        setSize(d.getWidth(), d.getHeight());
    }
    
	public void setSize(double width, double height) {
		this.width = width;
		this.height = height;
	}
	
	public double getWidth() {
		return width;
	}
	public void setWidth(double width) {
		this.width = width;
	}
	public double getHeight() {
		return height;
	}
	public void setHeight(double height) {
		this.height = height;
	}
}