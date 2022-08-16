function [stimuli,occluder] = makeUniformOccluders(stimuli,occluder_lb,occluder_rt,occluderColor)
    lb = min(occluder_lb);
    rt = max(occluder_rt);

    for l=1:2
        for s=1:size(stimuli,2)
            stimuli{l,s}.occluder.leftBottom = lb;
            stimuli{l,s}.occluder.rightTop = rt;   
            stimuli{l,s}.occluder.color = occluderColor;
        end
    end
    
    occluder.leftBottom = lb; 
    occluder.rightTop = rt;
    occluder.color = occluderColor;
end

