package org.xper.sach.drawing.splines;

public class MyPoint 
{
	public double x, y, z;

	MyPoint(MyPoint p)
	{
		x = p.x;
		y = p.y;
		z = p.z;
	}
	public MyPoint(double _x, double _y, double _z)
	{
		x = _x;
		y = _y;
		z = _z;
	}
	public MyPoint(double _x, double _y)
	{
		x = _x;
		y = _y;
		z = 0;
	}
	MyPoint()
	{
		x = 0;
		y = 0;
		z = 0;
	}
	void copy(MyPoint p)
	{
		x = p.x;
		y = p.y;
		z = p.z;
	}
	
	public void translateBy(MyPoint p) {
		x = x + p.x;
		y = y + p.y;
		z = z + p.z;
	}
}