package org.xper.allen.ga;

import org.xper.allen.util.TikTok;


import java.util.*;

public class ProbabilityTable<T> {
    private List<T> items;
    private List<Double> probabilities;
    private double[] cdf;

    public ProbabilityTable(List<T> items, List<Double> probabilities) {
        this.items = items;
        this.probabilities = probabilities;
        initTable();
    }

    public ProbabilityTable(Map<T, Double> probabilityForItems) {
        this.items = new ArrayList<T>();
        this.probabilities = new ArrayList<Double>();
        for (T key : probabilityForItems.keySet()) {
            items.add((T) key);
            probabilities.add(probabilityForItems.get(key));
        }
        initTable();
    }

    private void initTable() {
        TikTok timer = new TikTok("Normalize probability table");
        normalizeProbabilities();
        timer.stop();

        timer = new TikTok("Calculate CDF");
        calculate_cdf();
        timer.stop();
    }

    public T sampleWithReplacement() {
        TikTok timer = new TikTok("Sample with replacement");
        double rand = Math.random();
        for (int i=0; i<cdf.length; i++){
//            System.out.println(i + ": " + cdf[i]);
            if (rand < cdf[i]){
                return items.get(i);
            }
        }
        timer.stop();
        return null;
    }

    private void calculate_cdf() {
        cdf = new double[probabilities.size()];
        for (int i=0; i< probabilities.size(); i++){
            cdf[i] = probabilities.get(i);
            if (i > 0){
                cdf[i] += cdf[i-1];
            }
        }
    }

    private void normalizeProbabilities() {
        double sum = 0.0;
        for (double p : probabilities) {
            sum += p;
        }
        for (int i = 0; i < probabilities.size(); i++) {
            if (sum == 0.0){
                probabilities.set(i, 1.0/probabilities.size());
            } else {
                probabilities.set(i, probabilities.get(i) / sum);
            }
        }
    }

    public List<T> getItems() {
        return items;
    }

    public void setItems(List<T> items) {
        this.items = items;
    }

    public List<Double> getProbabilities() {
        return probabilities;
    }

    public void setProbabilities(List<Double> probabilities) {
        this.probabilities = probabilities;
    }
}