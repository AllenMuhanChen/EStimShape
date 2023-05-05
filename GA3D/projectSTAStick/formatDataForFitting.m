function [stim,resp,lineage,stimStruct,data_all] = formatDataForFitting(data_all)
    % maximum of 4 limbs
    % maximum of 6 roots
    % shaft (max 4): postion(3) + tangent(2) + width(1) + length(1) + curvature(1) = 8 
    % root (max 6): postion(3) + anglebisector(2) + width(1) + angle(1) + normal(1) = 8
    % terminal (max 4): postion(3) + tangent(2) + width(1) = 6
    % first 3 are nS, nR and nT
    stim_maxNumEl = 3 + 4*8 + 4*6 + 6*8;
    
    stim = nan(length(data_all),stim_maxNumEl);
    resp = nan(length(data_all),5);
     
    for stimNum=1:length(data_all)
        [stim_temp,stimStruct(stimNum),data_all(stimNum).rootComps] = ...
            getFittableStim(data_all(stimNum));
         
        % padding to max size
        stim_temp(end+1:stim_maxNumEl) = nan;
        stim(stimNum,:) = stim_temp;
        
        resp(stimNum,:) = removeoutliers(data_all(stimNum).resp);
    end
    lineage = [data_all.linNum];
    
    goodStim = sum(isnan(resp),2) <= 2;
    stim = stim(goodStim,:);
    resp = resp(goodStim,:);
    stimStruct = stimStruct(goodStim);
    lineage = lineage(goodStim);
end

function [stim,stimStruct,rootComps] = getFittableStim(data)   
    % get connectivity
    connMat = getConnMat(data.comp);
    
    % find two comps that are connected
    allJunc = find(tril(connMat) > 0);
    
%     scatter3(data.vert(:,1),data.vert(:,2),data.vert(:,3),15)
%     for ii=1:length(data.comp)
%         vv = data.comp(ii).pos;
%         hold on; scatter3(vv(1),vv(2),vv(3),5000,'Marker','.');
%     end
    
    % for each junction, get the root parameters
    rootComps = struct([]);
    for ii=1:length(allJunc)
        [a1,a2] = ind2sub(size(connMat),allJunc(ii));
    
        % find the root at which they are connected - R1R2
        r1_idx = connMat(a1,a2);
        r2_idx = connMat(a2,a1);

        p = data.comp(r1_idx).pos;
        t1 = data.comp(r1_idx).tangent;
        t2 = data.comp(r2_idx).tangent;
        
        bis = t1+t2;
        bis = bis/norm(bis);
        
        nn = cross(t1,t2);
        nn = nn/norm(nn);
        
%         p1 = findPtAlongVect(p,t1,1);
%         p2 = findPtAlongVect(p,t2,1);
%         p3 = findPtAlongVect(p,bis,1);
%         line([p(1) p1(1)],[p(2) p1(2)],[p(3) p1(3)],'linewidth',3);
%         line([p(1) p2(1)],[p(2) p2(2)],[p(3) p2(3)],'linewidth',3);
%         line([p(1) p3(1)],[p(2) p3(2)],[p(3) p3(3)],'linewidth',3);
%         
        ang = acos(dot(t1,t2));
%         disp(rad2deg(ang));
        k = pi/ang - 1;
        squashK = (2./(1+exp(-0.5*k))) - 1;
        
        rootComps(ii).pos = p;
        rootComps(ii).bis = bis;
        rootComps(ii).plane = nn;
        rootComps(ii).ang = ang;
        rootComps(ii).curv = squashK;
        rootComps(ii).rad = data.comp(r1_idx).rad;
    end
    data.rootComps = rootComps;
    
    % translate and scale the components based on the stim location and size
    % also convert to a flat component, if stim was 2d
    % finally, convert to 5/6 dim
    [finalShaftComp,finalRootComp,finalTermComp,...
        finalRootyShaftComp,finalTermyShaftComp] = transScaleComp(data);
    termIdx = cellfun(@(x) strcmp(x,'T'),{data.comp.compPart});
    shaftIdx = cellfun(@(x) strcmp(x,'S'),{data.comp.compPart});
    
    stim(1) = sum(shaftIdx);
    stim(2) = length(data.rootComps);
    stim(3) = sum(termIdx);
    
    temp = finalShaftComp'; stim = [stim temp(:)'];
    temp = finalRootComp'; stim = [stim temp(:)'];
    temp = finalTermComp'; stim = [stim temp(:)'];
    
    stimStruct.s = finalShaftComp';
    stimStruct.r = finalRootComp';
    stimStruct.t = finalTermComp';
    stimStruct.sr = finalRootyShaftComp';
    stimStruct.st = finalTermyShaftComp';
end

function [finalShaftComp,finalRootComp,finalTermComp,...
    finalRootyShaftComp,finalTermyShaftComp] = transScaleComp(data)
    % for each component
        % use x,y,z,s to translate and scale the pos
        % convert pos to sph
        % convert tangent to sph
        % scale the rad
        % change to 2d if necessary
        % finally, convert to 5d
        
    finalShaftComp = nan(length(data.fullComponents),8);
    finalRootComp = nan(length(data.rootComps),8);
    finalTermComp = nan(length(data.fullComponents),6);
    finalRootyShaftComp = nan(1,6); rootyShaftCount = 0;
    finalTermyShaftComp = nan(1,6); termyShaftCount = 0;
    
    s = data.s;
    
    % if you want to recenter to the fixation point based on the position
    % as is. This does not care about the center of mass of the object and
    % is faithful to how the stimulus is shown.
    x = data.x;
    y = data.y;
    z = data.z;
    centerOfMass = [x y z];
    maxRadDist = 1;
    
    
    % if you want to recenter to the fixation point based on the center of
    % mass of the object. also, this rescales all sizes/radii such that
    % they are relative to the size of the object.
    % data.vert = data.vert * data.s;
    % centerOfMass = (max(data.vert) + min(data.vert)) / 2;
    % data.vert = data.vert - repmat(centerOfMass,size(data.vert,1),1);
    % maxRadDist = max(sqrt(sum(data.vert.^2,2)));
    
    threeD = strcmp(data.texture,'SHADE') || strcmp(data.texture,'SPECULAR');
    for cc=1:length(data.comp)
        compNum = data.comp(cc).compNum;
        if strcmp(data.comp(cc).compPart,'T')
            pos = ((data.comp(cc).pos(:) .* s)' - centerOfMass) / maxRadDist;
            tan = data.comp(cc).tangent;
            if ~threeD
                pos(3) = 0;
                tan(3) = 0;
            end

            [pos_az,pos_el,pos_r] = cart2sph(pos(1),pos(2),pos(3));
            [tan_az,tan_el] = cart2sph(tan(1),tan(2),tan(3));
            rad = data.comp(cc).rad * s / maxRadDist;
            finalTermComp(compNum,:) = [pos_az,pos_el,pos_r,tan_az,tan_el,rad];
            if tan_el > 0 % data.comp(cc).rad > 0.8 && 
                k = 1/data.comp(cc).rad;
                squashK = (2./(1+exp(-0.5*k))) - 1;
                
                termyShaftCount = termyShaftCount + 1;
                finalTermyShaftComp(termyShaftCount,:) = [pos_az,pos_el,pos_r,tan_az,tan_el,squashK];
            end
        elseif strcmp(data.comp(cc).compPart,'S')
            pos = ((data.comp(cc).pos(:) .* s)' - centerOfMass) / maxRadDist;
            tan = data.comp(cc).tangent;
            if ~threeD
                pos(3) = 0;
                tan(3) = 0;
            end

            [pos_az,pos_el,pos_r] = cart2sph(pos(1),pos(2),pos(3));
            [tan_az,tan_el] = cart2sph(tan(1),tan(2),tan(3));
            rad = data.comp(cc).rad * s / maxRadDist;
            if tan_el < 0 && tan_az > 0
                tan_az = tan_az - pi; tan_el = -tan_el;
            elseif tan_el < 0 && tan_az < 0
                tan_az = tan_az + pi; tan_el = -tan_el;
            end
            sLength = data.compLengths(compNum) * s / maxRadDist;
            sCurv = data.compCurves(compNum);
            finalShaftComp(compNum,:) = [pos_az,pos_el,pos_r,tan_az,tan_el,rad,sLength,sCurv];
            
            if ~isnan(data.shaftBis(compNum,1)) && data.compCurves(compNum) > 0.3
                if ~threeD
                    data.shaftBis(3) = 0;
                end
                [tan_az,tan_el] = cart2sph(data.shaftBis(compNum,1),data.shaftBis(compNum,2),data.shaftBis(compNum,3));
                if tan_el > 0
                    rootyShaftCount = rootyShaftCount + 1;
                    finalRootyShaftComp(rootyShaftCount,:) = [pos_az,pos_el,pos_r,tan_az,tan_el,data.compCurves(compNum)];
                else
                    termyShaftCount = termyShaftCount + 1;
                    [tan_az,tan_el] = cart2sph(-data.shaftBis(compNum,1),-data.shaftBis(compNum,2),-data.shaftBis(compNum,3));
                    finalTermyShaftComp(termyShaftCount,:) = [pos_az,pos_el,pos_r,tan_az,tan_el,data.compCurves(compNum)];
                end
            end
        end
    end
    
    for cc=1:length(data.rootComps)
        pos = ((data.rootComps(cc).pos(:) .* s)' - centerOfMass) / maxRadDist;
        tan = data.rootComps(cc).bis;
        plane = data.rootComps(cc).plane;
        if ~threeD
            pos(3) = 0;
            tan(3) = 0;
        end
        
        [pos_az,pos_el,pos_r] = cart2sph(pos(1),pos(2),pos(3));
        [tan_az,tan_el] = cart2sph(tan(1),tan(2),tan(3));
        [~,plane_el] = cart2sph(plane(1),plane(2),plane(3));
        rad = data.rootComps(cc).rad * s / maxRadDist;
        finalRootComp(cc,:) = [pos_az,pos_el,pos_r,tan_az,tan_el,rad,data.rootComps(cc).ang,plane_el];
%         if tan_el > 0
            rootyShaftCount = rootyShaftCount + 1;
            finalRootyShaftComp(rootyShaftCount,:) = [pos_az,pos_el,pos_r,tan_az,tan_el,data.rootComps(cc).curv];
        % else
        %     termyShaftCount = termyShaftCount + 1;
        %     finalTermyShaftComp(termyShaftCount,:) = [pos_az,pos_el,pos_r,tan_az,tan_el,rad];
%         end
            
    end
    finalTermComp(isnan(finalTermComp(:,1)),:) = [];
end

function connMat = getConnMat(comp)
    nComp = max([comp.compNum]);
    rootIdx = cellfun(@(x) strcmp(x,'R'),{comp.compPart});
    compsWithRoots = unique([comp.compNum] .* rootIdx); compsWithRoots(compsWithRoots==0) = [];
    
    connMat = zeros(nComp);
    for ii=1:length(compsWithRoots)
        comp1 = compsWithRoots(ii);
        for jj=ii+1:length(compsWithRoots)
            if ii ~= jj
                comp2 = compsWithRoots(jj);

                compsToCheck = find(([comp.compNum] == comp1 .* rootIdx) + ([comp.compNum] == comp2 .* rootIdx));
                allPos = {comp.pos}';
                allPos = allPos(compsToCheck);
                [~,b,c] = unique(cell2mat(allPos),'rows');
                
                if length(b) < length(allPos)
                    temp = zeros(1,length(comp));
                    if sum(c) == 5 || sum(c) == 8
                        temp(compsToCheck(~(c-2))) = 1;
                    elseif sum(c) == 9
                        temp(compsToCheck(~(c-3))) = 1;
                    else
                        temp(compsToCheck(~(c-1))) = 1;
                    end
                    connMat(comp1,comp2) = find([comp.compNum] == comp1 .* rootIdx .* temp);
                    connMat(comp2,comp1) = find([comp.compNum] == comp2 .* rootIdx .* temp);
                end
            end
        end
    end
end

function dataout = removeoutliers(datain)
    %REMOVEOUTLIERS   Remove outliers from data using the Thompson Tau method.
    %   For vectors, REMOVEOUTLIERS(datain) removes the elements in datain that
    %   are considered outliers as defined by the Thompson Tau method. This
    %   applies to any data vector greater than three elements in length, with
    %   no upper limit (other than that of the machine running the script).
    %   Additionally, the output vector is sorted in ascending order.
    %
    %   Example: If datain = [1 34 35 35 33 34 37 38 35 35 36 150]
    %
    %   then removeoutliers(datain) will return the vector:
    %       dataout = 33 34 34 35 35 35 35 36 37 38
    %
    %   See also MEDIAN, STD, MIN, MAX, VAR, COV, MODE.
    %   This function was written by Vince Petaccio on July 30, 2009.
    n=length(datain); %Determine the number of samples in datain
    if n < 3
        disp(['ERROR: There must be at least 3 samples in the' ...
            ' data set in order to use the removeoutliers function.']);
    else
        S=std(datain); %Calculate S, the sample standard deviation
        xbar=mean(datain); %Calculate the sample mean
        %tau is a vector containing values for Thompson's Tau
        tau = [1.150 1.393 1.572 1.656 1.711 1.749 1.777 1.798 1.815 1.829 ...
            1.840 1.849 1.858 1.865 1.871 1.876 1.881 1.885 1.889 1.893 ...
            1.896 1.899 1.902 1.904 1.906 1.908 1.910 1.911 1.913 1.914 ...
            1.916 1.917 1.919 1.920 1.921 1.922 1.923 1.924];
        %Determine the value of S times Tau
        if n > length(tau)
            TS=1.960*S; %For n > 40
        else
            TS=tau(n)*S; %For samples of size 3 < n < 40
        end
        %Sort the input data vector so that removing the extreme values
        %becomes an arbitrary task
        dataout = sort(datain);
        %Compare the values of extreme high data points to TS
        while abs((max(dataout)-xbar)) > TS 
            dataout=dataout(1:(length(dataout)-1));
            %Determine the NEW value of S times Tau
            S=std(dataout);
            xbar=mean(dataout);
            if length(dataout) > length(tau)
                TS=1.960*S; %For n > 40
            else
                TS=tau(length(dataout))*S; %For samples of size 3 < n < 40
            end
        end
        %Compare the values of extreme low data points to TS.
        %Begin by determining the NEW value of S times Tau
            S=std(dataout);
            xbar=mean(dataout);
            if length(dataout) > length(tau)
                TS=1.960*S; %For n > 40
            else
                TS=tau(length(dataout))*S; %For samples of size 3 < n < 40
            end
        while abs((min(dataout)-xbar)) > TS 
            dataout=dataout(2:(length(dataout)));
            %Determine the NEW value of S times Tau
            S=std(dataout);
            xbar=mean(dataout);
            if length(dataout) > length(tau)
                TS=1.960*S; %For n > 40
            else
                TS=tau(length(dataout))*S; %For samples of size 3 < n < 40
            end
        end
    end
    dataout = [dataout; nan(length(datain)-length(dataout),1)];
end

