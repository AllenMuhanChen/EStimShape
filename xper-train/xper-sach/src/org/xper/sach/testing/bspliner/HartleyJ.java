package org.xper.sach.testing.bspliner;

public class    HartleyJ   
{   
    public static void main(String[] args)    
    {   
        double[][] d ={{-24,-12,1,10,12},{0,6,8,2,0}};   
        int n=5;   
        int k=3;   
        double[] u=new double[n+k+1];   
        HartleyJ H=new HartleyJ();   
        u=H.Hartleyknot(d,n,k);   
           
        double[]  w=H.HartleyT(u,n,k);   
        for(int i=0;i<w.length;i++)   
            System.out.println(w[i]);   
        for(int i=0;i<n+k+1;i++)   
        System.out.println("U="+u[i]+"   ");   
    }   
    public  double sum(double[][] d,int n,int j)   // this sums the distances between successive points from j to n-1 (zero indexed)
    {   
        double L=0;   
        double[] l=new double[n];   
        for(int i=n-1;i>j;i--)   
        {   
            l[i]=Math.sqrt((d[0][i]-d[0][i-1])*(d[0][i]-d[0][i-1])+(d[1][i]-d[1][i-1])*(d[1][i]-d[1][i-1]));   
            L=L+l[i];   
        }      
        return L;   
    }   
    public  double Sum(double[][] d,int k,int  n)   // sum of sums over interval
    {   
        double Sum1=0;   
        for(int i=k+1;i<=n;i++)   
        {   
            Sum1=Sum1+sum(d,i,i-k-1);   
        }   
        return Sum1;   
   
    }   
    public  double[] Hartleyknot(double[][] d,int n,int k)   
    {    
        double[] u=new double[n+k+1];   			// 5+3+1
        double U=0;   
        for(int j=0;j<=k;j++)   					// from 0 to 3
            u[j]=0;   								// [0 0 0 0 - - - - -]
        for(int i=k+1;i<=n-1;i++)   				// from 4 to 4
        {   
            for(int j=k+1;j<=i;j++)   				// from 4 to 4
            {   
                U=U+sum(d,j,j-k-1)/Sum(d,k,n);   	// 0 + sum(d_arr,4,0) / Sum(d,3,5) -> 
            }   
            u[i]=U;   								// [0 0 0 0 u[i] - - - -]
        }   
        for(int j=n;j<n+k+1;j++)   					// sets the rest to 1
        {   
            u[j]=1;   
        }   
        return u;   								// [0 0 0 0 0.481 1 1 1 1]
    }   
    public double[] HartleyT(double[] u,int n,int k)   
    {   
        double[] w=new double[n-k-1+2];   	// 5-3-1+2=3
        for(int i=0;i<w.length;i++)   		// [- - -]
            w[i]=u[i+k];   					// middle 3 members of the u array: [0 0.48 1] 
        return w;   
    }   
   
}   
