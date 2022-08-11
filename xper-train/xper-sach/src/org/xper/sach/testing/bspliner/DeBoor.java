package org.xper.sach.testing.bspliner;

public class DeBoor     
{   
    public static void main(String[] args)    
    {   
        DeBoor D=new DeBoor();   
        double[][] d={{-24,-12,1,10,12},{0,6,8,2,0}};   
        double[] t={0,0.75,1};   
        int [] r={4,1,4};   
        int q=2;   
        int k=3;   
        double u=0.5;   
        double[] w=D.BsplineDrive(d,t,r,q,u,k);   
        System.out.println(w[0]+" "+w[1]);   
    }   
    public   double[]  BsplineNote(double[] t,int[] r,double u,double[][] d)   
    {       
        double x[]=new double[2];   
        double[][] c=d;   
        int i=0,k=3;   
        for(int j=0;j<8;j++)   
        {   
            if(u<=knotValue(j+1,t,r)&&u>knotValue(j,t,r))   
            {   
                i=j;   
                break;   
            }   
        }   
           
       
           
           
        for(int q=1;q<=k;q++)   
        {   
            for(int j=i-k;j<=i-q;j++)   
            {   
                double alfa=knotValue(j+k+1,t,r)-knotValue(j+1,t,r);   
                if(alfa==0)alfa=0;   
                else   
                alfa=(u-knotValue(j+1,t,r))/alfa;   
                c[0][j]=(1-alfa)*c[0][j]+alfa*c[0][j+1];   
                c[1][j]=(1-alfa)*c[1][j]+alfa*c[1][j+1];   
            }   
        }   
        for(int m=0;m<2;m++)   
        {   
            x[m]=c[m][i-k];   
        }    
            
        return x;    
    }   
    public double[] BsplineDrive(double[][] d,double[] t,int[] r,int q,double u,int k)   
    {   
        // NOT SURE WHAT THIS NOTE WAS   
        double[] x=new double[2];   
        int i=0;   
        for(int j=0;j<d[0].length-1;j++)   
        {   
            if(u<=knotValue(j+1,t,r)&&u>knotValue(j,t,r))   
            {   
                i=j;   
                break;   
            }   
        }   
        //System.out.println(i);   
        for(int l=1;l<=q;l++)   
        {   
            for(int j=i-k;j<=i-l;j++)   
            {   
                d[0][j]=(k-l+1)*(d[0][j+1]-d[0][j])/(knotValue(j+k+1,t,r)-knotValue(j+l,t,r));   
                d[1][j]=(k-l+1)*(d[1][j+1]-d[1][j])/(knotValue(j+k+1,t,r)-knotValue(j+l,t,r));   
            }   
        }    
        for(int j=0;j<=i-q;j++)   
        //System.out.print(d[0][j]+" "+d[1][j]+"  ");   
        for(int l=1;l<=i-q;l++)   
        {   
            for(int j1=0;j1<i-q;j1++)   
            {   
                double alfa=knotValue(j1+k+1,t,r)-knotValue(j1+q+1,t,r);   
                if(alfa==0)alfa=0;   
                else    
                    alfa=(u-knotValue(j1+q+1,t,r))/alfa;   
                d[0][j1]=(1-alfa)*d[0][j1]+alfa*d[0][j1+1];   
                d[1][j1]=(1-alfa)*d[1][j1]+alfa*d[1][j1+1];   
            }   
        }   
        x[0]=d[0][0];x[1]=d[1][0];   
        return x;   
    }   
    public double knotValue(int k,double t[],int r[])   
    {   
        int j=1;   
        double temp=0;   
        for(int i=0;i<r.length;i++)   
        {   
            temp=temp+r[i];   
            if(temp>k)   
            {   
                j=i;   
                break;   
            }   
        }   
        return t[j];   
           
    }   
}   
