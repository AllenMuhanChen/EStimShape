package org.xper.time;

public class TicToc {
    private static long start;

    public static void tic(){
        start = System.nanoTime();
    }

    public static long toc(){
        return (System.nanoTime() - start)/1000000;
    }

}
