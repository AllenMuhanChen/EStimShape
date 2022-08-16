function color = getShapeColor(fColor)
    colorIdx = datasample(1:length(fColor.options),1,'weights',fColor.prob);
    color = fliplr(de2bi(fColor.options(colorIdx),3));
end