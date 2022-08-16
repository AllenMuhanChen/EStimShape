function stim = applyMorphs(parentStim)  
    stim = parentStim;
%     if rand > 0.5
        stim = applyMorphs_mstick(stim);
%     else
%         stim = applyMorphs_non_mstick(stim);
%     end
end

function stim = applyMorphs_mstick(stim)
    stim.id.tagForMorph = true;
end

function stim = applyMorphs_non_mstick(stim)
    switch randi(4)
        case 1; stim = morph_shape_pos(stim);
        case 2; stim = morph_shape_siz(stim);
        case 3; stim = morph_shape_toggleOccluder(stim);
        case 4; stim = morph_shape_singleMask(stim);
%         case 5; stim = morph_shape_newAperture(stim);
    end
end

function stim = morph_shape_siz(stim)
    % size morph changes shape size by a random amount drawn from a
    % chi2 distribution (k=16) multiplied by a factor of the morph level. 
    % The size change is randomly reciprocated to account for size 
    % increases and decreases. So at morph level 4 the mean morph is 
    % + or - 20deg. At morph level 1, mean is + or - 5deg. 
    % Maximum morph is 40 deg. Minimum morph is 5deg.
    
    % get s change; max 2x; min 1.2x
    s = 3;
    while s > 2 || s < 1.2
        s = (chi2rnd(30,1)/30)*2;
    end
    
    % take reciprocal
    if rand > 0.5; s = 1/s; end
    
    stim.shape.s = stim.shape.s * s;
end

function stim = morph_shape_pos(stim)
    % pos morph changes shape pos by a random amount drawn from a
    % chi2 distribution (k=10) multiplied by a factor of the morph level. 
    % The direction of pos morph is random. So at morph level 4 the 
    % mean morph is 2deg in any dir. At morph level 1, mean is 0.4deg. 
    % Maximum morph is 3 deg. Minimum morph is 0.2deg.

    % pos morph needs screen distance so load the file to get it
    getPaths;
    load([rootPath '/currentGAInfo.mat']); 
    
    % get r change; max 4deg; min 0.2deg
    r = 3;
    while r > 2 || r < 0.2
        r = chi2rnd(10,1)*(1/20);
    end
    
    % convert r from deg to mm
    r = screen.dist * tan(deg2rad(r));
    
    % get random direction
    th = 2*pi*rand;
    
    % get x and y
    [x,y] = pol2cart(th,r);
    
    % assign to shape
    stim.shape.x = stim.shape.x + x;
    stim.shape.y = stim.shape.y + y;
end

function stim = morph_shape_toggleOccluder(stim)
    stim.id.isOccluded = ~stim.id.isOccluded;
end

function stim = morph_shape_singleMask(stim)
    activeMasks = [stim.mask.isActive];
    bothActive = isequal(activeMasks,ones(1,2));
    if ~bothActive
        activeMasks = ~activeMasks;
    else
        activeMasks(randi(2)) = 0;    
    end
    stim.mask(1).isActive = activeMasks(1);
    stim.mask(2).isActive = activeMasks(2);
end