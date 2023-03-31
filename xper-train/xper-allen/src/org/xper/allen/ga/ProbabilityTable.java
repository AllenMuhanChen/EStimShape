package org.xper.allen.ga;

import java.util.*;

public class ProbabilityTable<T> {
    private List<T> items;
    private List<Double> probabilities;

    public ProbabilityTable(List<T> items, List<Double> probabilities) {
        this.items = items;
        this.probabilities = probabilities;
        normalizeProbabilities();
    }

    public ProbabilityTable(Map<T, Double> probabilityForItems) {
        this.items = new ArrayList<T>();
        this.probabilities = new ArrayList<Double>();
        for (T key : probabilityForItems.keySet()) {
            items.add((T) key);
            probabilities.add(probabilityForItems.get(key));
        }
        normalizeProbabilities();
    }

    public T sampleWithReplacement() {
        double rand = Math.random();
        double cumProb = 0.0;
        for (int i = 0; i < probabilities.size(); i++) {
            cumProb += probabilities.get(i);
            if (rand < cumProb) {
                return items.get(i);
            }
        }
        return null;
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