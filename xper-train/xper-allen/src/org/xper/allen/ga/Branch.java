package org.xper.allen.ga;

import com.thoughtworks.xstream.XStream;

import java.util.Collection;
import java.util.LinkedList;
import java.util.List;
import java.util.Objects;
import java.util.function.Consumer;
import java.util.function.Predicate;

public class Branch<T> {

    private Collection<Branch<T>> children;
    private T identifier;

    public Branch(T identifier){
        this.identifier = identifier;
        this.children = new LinkedList<>();
    }

    public void addChild(Branch<T> child){
        children.add(child);
    }

    /**
     * Adds a child to the branch with the specified identifier. The specified identifier
     * can be the identifier for any of the branches in the tree.
     *
     * @param childBranch the branch to add as a child
     */
    public void addChildTo(T parentId, Branch<T> childBranch) {
        if (this.identifier == parentId){
            this.addChild(childBranch);
        } else {
            for (Branch<T> child : children){
                child.addChildTo(parentId, childBranch);
            }
        }
    }

    /**
     * Adds a child to the branch with the specified identifier. The specified identifier
     * can be the identifier for any of the branches in the tree.
     *
     * @param childId given identifier for the child branch, will create a new branch with this identifier to add
     */
    public void addChildTo(T parentId, T childId) {
        if (this.identifier.equals(parentId)){
            this.addChild(new Branch<T>(childId));
        } else {
            for (Branch<T> child : children){
                child.addChildTo(parentId, childId);
            }
        }
    }

    public void forEach(Consumer<? super Branch<T>> action) {
        action.accept(this);
        for (Branch<T> child : children){
            child.forEach(action);
        }
    }

    public Branch<T> findParentOf(T childId) {
        if (this.children.stream().anyMatch(new Predicate<Branch<T>>() {
            @Override
            public boolean test(Branch<T> branch) {
                return branch.identifier.equals(childId);
            }
        })){
            return this;
        } else {
            for (Branch<T> child : children){
                Branch<T> parent = child.findParentOf(childId);
                if (parent != null){
                    return parent;
                }
            }
        }
        return null;
    }

    public List<T> findSiblingsOf(T id) {
        List<T> siblings = new LinkedList<>();
        if (this.children.stream().anyMatch(new Predicate<Branch<T>>() {
            @Override
            public boolean test(Branch<T> branch) {
                return branch.identifier.equals(id);
            }
        })){
            for (Branch<T> child : children){
                if (!child.identifier.equals(id)){
                    siblings.add(child.identifier);
                }
            }
        } else {
            for (Branch<T> child : children){
                List<T> childSiblings = child.findSiblingsOf(id);
                if (childSiblings != null){
                    siblings.addAll(childSiblings);
                }
            }
        }
        return siblings;
    }

    static XStream s;

    static{
        s = new XStream();
        s.alias("GABranch", Branch.class);
        s.aliasField("identifier", Branch.class, "identifier");
    }

    /**
     * For XStream, shouldn't be called directly.
     */
    private Branch() {
    }

    public String toXml(){
        return Branch.toXml(this);
    }

    public static String toXml(Branch branch){
        return s.toXML(branch);
    }

    public static Branch fromXml(String xml){
        return (Branch) s.fromXML(xml);
    }

    public Collection<Branch<T>> getChildren() {
        return children;
    }

    public void setChildren(Collection<Branch<T>> children) {
        this.children = children;
    }

    public T getIdentifier() {
        return identifier;
    }

    public void setIdentifier(T identifier) {
        this.identifier = identifier;
    }

    @Override
    public String toString() {
       String s = identifier + "\n";
         for (Branch<T> child : children){

              s += "-"+child.toString();
         }
           return s;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Branch<T> branch = (Branch<T>) o;
        return getChildren().equals(branch.getChildren()) && getIdentifier().equals(branch.getIdentifier());
    }

    @Override
    public int hashCode() {
        return Objects.hash(getChildren(), getIdentifier());
    }

    public Branch<T> find(T id) {
        if (this.identifier.equals(id)){
            return this;
        } else {
            for (Branch<T> child : children){
                Branch<T> found = child.find(id);
                if (found != null){
                    return found;
                }
            }
        }
        return null;
    }
}